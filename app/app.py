"""
Authors:
Fred Kerr
Daniel Beidelschies
Radu Lungu
"""

import json
import random

import sqlalchemy.exc

from flask import Flask, render_template, request
from flask_sqlalchemy import SQLAlchemy
from flask_socketio import SocketIO, send, join_room, emit

# Configuring the flask app and the SQLAlchemy database
app = Flask(__name__)
app.config.from_pyfile('app.cfg')
socketio = SocketIO(app, cors_allowed_origins='*')
db = SQLAlchemy(app)


# Creating the database
class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.String(200))
    username = db.Column(db.String(200), primary_key=True, nullable=False)
    team = db.Column(db.Integer)
    drawer = db.Column(db.Boolean)

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
    json_data = json.loads(msg)
    emit('message', msg, room=json_data.get('room'), include_self=False)


# App endpoint to expose the playing room based on users
@app.route('/play/<username>')
def play(username):

    # Querying the database for various state variables
    team1 = User.query.filter_by(team=0)
    team2 = User.query.filter_by(team=1)
    team1_score = 0 if Data.query.filter_by(type='team0_score').first() is None else Data.query.filter_by(
        type='team0_score').first().value
    team2_score = 0 if Data.query.filter_by(type='team1_score').first() is None else Data.query.filter_by(
        type='team1_score').first().value
    user = User.query.filter_by(username=username).first()

    # Getting a random noun from the local work bank and copying it to the database
    try:
        word = get_random_noun()
        db.session.add(Data(type='word', value=word))
        db.session.commit()
    except sqlalchemy.exc.IntegrityError:
        db.session.rollback()
        word = Data.query.filter_by(type='word').first().value

    # Render the html template with the above state variables
    return render_template("draw.html",
                           team1=team1,
                           team2=team2,
                           username=username,
                           drawer=user.drawer,
                           team=user.team,
                           word_to_guess=word,
                           team1_score=team1_score,
                           team2_score=team2_score)


# App endpoint to expose the lobby page
@app.route('/')
def lobby():
    return render_template("index.html", users=User.query.all())


# Socket.io function to handle new users joining the game
@socketio.on('joinUsername')
def receive_username(username):

    try:
        # Check that the user is not in the database already, according to sid
        if User.query.filter_by(id=request.sid).first() is None:
            len_team1 = User.query.filter_by(team=0).count()
            len_team2 = User.query.filter_by(team=1).count()

            # Add user to database based on teams lenght
            if len_team1 <= len_team2:
                add_teamMember(0, username, len_team1)
                team = 0
            else:
                add_teamMember(1, username, len_team2)
                team = 1
            send(json.dumps({'username': username, 'team': team}), broadcast=True)
        else:
            send("userErrorMessage")
    except sqlalchemy.exc.IntegrityError:
        send("userErrorMessage")

    # If there are more than 4 users, start the game and move all users to the play room.
    if User.query.count() >= 4:
        send("startGameMessage", broadcast=True)


# Socket.io function to add users to specific rooms
@socketio.on('join_room')
def add_to_room(msg):
    join_room(msg)


# Function to add users to the database
def add_teamMember(team, username, length):
    if length == 0:
        new_user = User(id=request.sid, username=username, team=team, drawer=True)
    else:
        new_user = User(id=request.sid, username=username, team=team, drawer=False)
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
    existing_word = Data.query.filter_by(type='word').first().value

    # If the team guess is equal to the word in the database
    if msg['guess'].casefold() == existing_word.casefold():
        # Reset the word and update score
        reset()
        score = updateScore(msg['team'])

        # If score is 5 then restart the game
        if score == 5:
            db.drop_all()
            db.create_all()
            send('reset', broadcast=True)
        else:
            send('game_over', broadcast=True)


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
def reset():
    word = Data.query.get('word')
    db.session.delete(word)
    db.session.commit()


if __name__ == '__main__':
    socketio.run(app)
