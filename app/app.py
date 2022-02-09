"""
Authors:
Fred Kerr
Daniel Beidelschies
Radu Lungu
"""

import json
import math
import random

import sqlalchemy.exc

from flask import Flask, render_template, request
from flask_sqlalchemy import SQLAlchemy
from flask_socketio import SocketIO, send, join_room, emit, leave_room

# Configuring the flask app and the SQLAlchemy database
app = Flask(__name__)
app.config.from_pyfile('app.cfg')
socketio = SocketIO(app, cors_allowed_origins='*')
db = SQLAlchemy(app)


# Creating the database
class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.String(200))
    userCode = db.Column(db.String(50))
    username = db.Column(db.String(200), primary_key=True, nullable=False)
    team = db.Column(db.Integer)
    drawer = db.Column(db.Boolean)
    inGame = db.Column(db.Boolean)

    def __repr__(self):
        return self.username


# Defining the data model
class Data(db.Model):
    __tablename__ = 'data'
    type = db.Column(db.String(30), primary_key=True)
    value = db.Column(db.String(30), nullable=False)

    def __repr__(self):
        return self.value


# General Socket.io function to handle unnamed incoming messages
@socketio.on('message')
def handleMessage(msg):
    emit('message', msg, room=msg.get('room'), include_self=False)


@socketio.on('load_canvas')
def handleLoadCanvas(msg):
    emit('load_canvas', msg.get('from'), room=msg.get('team'), include_self=False)


@socketio.on('send_canvas')
def handleSendCanvas(msg):
    room = User.query.get(msg.get('room')).id
    del msg['room']
    emit('message', msg, room=room, include_self=False)


# App endpoint to expose the playing room based on users
@app.route('/play/<user_code>')
def play(user_code):
    # Querying the database for various state variables
    user = User.query.filter_by(userCode=user_code).first()
    # user.inGame = True
    db.session.commit()
    base_team = math.floor(user.team / 2) * 2
    team1 = User.query.filter_by(team=base_team)
    team2 = User.query.filter_by(team=base_team + 1)
    team1_score = Data.query.get('team' + str(base_team) + '_score')
    team2_score = Data.query.get('team' + str(base_team + 1) + '_score')
    team1_score = 0 if team1_score is None else team1_score
    team2_score = 0 if team2_score is None else team2_score

    # Getting a random noun from the local work bank and copying it to the database
    try:
        word = get_random_noun()
        db.session.add(Data(type='baseTeam' + str(base_team) + '_word', value=word))
        db.session.commit()
    except sqlalchemy.exc.IntegrityError:
        db.session.rollback()
        word = Data.query.get('baseTeam' + str(base_team) + '_word').value

    # Render the html template with the above state variables
    return render_template("draw.html",
                           team1=team1,
                           team2=team2,
                           username=user.username,
                           user_code=user_code,
                           drawer=user.drawer,
                           team=user.team,
                           word_to_guess=word,
                           team1_score=team1_score,
                           team2_score=team2_score)


# App endpoint to expose the lobby page
@app.route('/')
def lobby():
    return render_template("index.html", users=User.query.filter_by(inGame=False))


# Socket.io function to handle new users joining the game
@socketio.on('joinUsername')
def receive_username(msg):
    user_count = User.query.count()
    try:
        # Check that the user is not in the database already, according to sid
        if User.query.filter_by(id=request.sid).first() is None:

            # Add user to database based on teams lenght
            base_team = math.floor(user_count / 8) * 2
            if User.query.filter_by(team=base_team).count() <= User.query.filter_by(team=base_team+1).count():
                team = base_team
            else:
                team = base_team+1
            print("User code; " + msg['userCode'])
            add_teamMember(team, msg['username'], msg['userCode'])
            emit('message', {'username': msg['username'], 'team': team}, broadcast=True)

            # If there are more than 4 users, start the game and move all users to the play room.
            user_count += 1
            if user_count % 4 == 0:
                if user_count % 8 == 0:
                    for user in User.query.all():
                        user.inGame = True
                    db.session.commit()
                    emit('max_users_reached', str(user_count), broadcast=True)
                    send("startGameMessage", to=request.sid, broadcast=False)
                else:
                    send("startGameMessage", broadcast=True)
            elif user_count % 8 > 4:
                send("startGameMessage", to=request.sid, broadcast=False)
        else:
            send("userErrorMessage")
    except sqlalchemy.exc.IntegrityError:
        send("userErrorMessage")


# Socket.io function to add users to specific rooms
@socketio.on('join_room')
def add_to_room(msg):
    join_room(msg.get('team'))
    User.query.get(msg.get('username')).id = request.sid
    db.session.commit()


# Function to add users to the database
def add_teamMember(team, username, user_code):
    if User.query.filter((User.team == team) & User.drawer).count() == 0:
        new_user = User(id=request.sid, userCode=user_code, username=username, team=team, drawer=True, inGame=False)
    else:
        new_user = User(id=request.sid, userCode=user_code, username=username, team=team, drawer=False, inGame=False)
    db.session.add(new_user)
    db.session.commit()


# Function to get a random nous from static/words.txt
def get_random_noun():
    lines = open('static/words.txt').read().splitlines()
    return random.choice(lines).capitalize()


# Socket.io function to handle the guessing logic
@socketio.on('guess')
def validate_guess(msg):
    # Query the database for the current word to guess
    existing_word = Data.query.get('baseTeam' + str(math.floor(msg['team'] / 2) * 2) + '_word').value
    # If the team guess is equal to the word in the database
    if msg['guess'].casefold() == existing_word.casefold():
        # Reset the word and update score
        reset(msg['team'])
        score = updateScore(msg['team'])

        # If score is 5 then restart the game
        base_team = math.floor(msg['team'] / 2) * 2
        if score == 5:
            delete_users(base_team)
            emit('message', 'reset', room=str(base_team))
            emit('message', 'reset', room=str(base_team + 1))
        else:
            emit('message', 'game_over', room=str(base_team))
            emit('message', 'game_over', room=str(base_team + 1))


# Function to update score based on the team
def updateScore(team):
    data_type = 'team' + str(team) + '_score'
    if Data.query.filter_by(type=data_type).first() is None:
        db.session.add(Data(type=data_type, value="1"))
        score = '1'
    else:
        existing_score = Data.query.get(data_type)
        existing_score.value = str(int(existing_score.value) + 1)
        score = existing_score.value
    db.session.commit()
    return int(score)


# Function to reset the word to guess in the database
def reset(team):
    base_team = math.floor(team / 2) * 2
    word = Data.query.get('baseTeam' + str(base_team) + '_word')
    db.session.delete(word)
    db.session.commit()


def delete_users(base_team):
    for user in User.query.filter((User.team == base_team) | (User.team == base_team + 1)).all():
        db.session.delete(user)
    for item in Data.query.all():
        db.session.delete(item)
    db.session.commit()


@socketio.on('delete_user')
def delete_user(msg):
    user = User.query.get(msg)
    leave_room(str(user.team))
    db.session.delete(user)
    db.session.commit()
    base_team = math.floor(user.team / 2) * 2
    emit('delete_user', msg, broadcast=True)
    if user.drawer and user.inGame:
        delete_users(base_team)
        emit('message', 'force_reset', room=str(base_team))
        emit('message', 'force_reset', room=str(base_team + 1))


if __name__ == '__main__':
    socketio.run(app)
