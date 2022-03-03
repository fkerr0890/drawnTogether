"""
Authors:
Fred Kerr
Daniel Beidelschies
Radu Lungu
"""

import math
import random

import sqlalchemy.exc

from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_socketio import SocketIO, send, join_room, emit, leave_room, close_room, rooms

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
    cached = db.Column(db.Boolean)

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
    emit('message', msg, room=msg['room'], include_self=False)


@socketio.on('load_canvas')
def handleLoadCanvas(msg):
    team = User.query.filter((User.team == msg['team']) & (User.cached == False))
    in_room_count = 0
    for user in team:
        print("User " + user.username + " rooms: " + str(rooms(user.id)))
        if rooms(user.id).count(msg['team']) > 0:
            in_room_count += 1
    print("in room count: " + str(in_room_count) + ", team count: " + str(team.count()))
    if in_room_count == team.count():
        print("load")
        emit('load_canvas', msg['from'], room=msg['team'], include_self=False)


@socketio.on('send_canvas')
def handleSendCanvas(msg):
    room = User.query.get(msg.get('room')).id
    del msg['room']
    emit('message', msg, room=room, include_self=False)

@socketio.on('send_winning_canvas')
def handleSendWinningCanvas(msg):
    user = User.query.get(msg['user'])
    if user is not None:
        base_team = math.floor(user.team / 2) * 2
        print("base team: " + str(base_team) + ", team: " + str(user.team))
        emit('winning_canvas', msg, room=str(base_team), include_self=False)
        emit('winning_canvas', msg, room=str(base_team+1), include_self=False)

@socketio.on('send_current_countdown')
def handleSendCurrentCountdown(msg):
    print("time remaining: " + str(msg))
    base_team = Data.query.get('incomplete')
    sender = User.query.filter_by(id=request.sid).first()
    if base_team is not None and sender is not None:
        if base_team.value == str(math.floor(sender.team / 2) * 2):
            print("Sending current countdown")
            emit('current_countdown', msg, broadcast=True)



# App endpoint to expose the playing room based on users
@app.route('/play/<user_code>')
def play(user_code):
    # Querying the database for various state variables
    user = User.query.filter_by(userCode=user_code).first()
    if user is None:
        return redirect(url_for('lobby'))
    else:
        user.inGame = True
        rejoin = False
        print(user.username + " cached " + str(user.cached))
        if user.cached:
            user.cached = False
            rejoin = True
        db.session.commit()
        base_team = math.floor(user.team / 2) * 2
        team1 = User.query.filter((User.team == base_team) & (User.cached == False))
        team2 = User.query.filter((User.team == base_team+1) & (User.cached == False))
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
                               team1=team1.all(),
                               team2=team2.all(),
                               username=user.username,
                               user_code=user_code,
                               drawer=user.drawer,
                               team=user.team,
                               word_to_guess=word,
                               team1_score=team1_score,
                               team2_score=team2_score,
                               rejoin=rejoin)


# App endpoint to expose the lobby page
@app.route('/')
def lobby():
    try:
        User.query.all()
    except sqlalchemy.exc.OperationalError:
        db.create_all()
    base_team = Data.query.get('incomplete')
    if base_team is not None:
        base_team = int(base_team.value)
        users = User.query.filter(((User.team == base_team) | (User.team == base_team + 1)) & (User.cached == False)).all()
    else:
        users = []
    return render_template("index.html", users=users)


# Socket.io function to handle new users joining the game
@socketio.on('joinUsername')
def receive_username(msg):
    base_team, user_count = retrieve_incomplete_team()
    try:
        # Check that the user is not in the database already, according to sid
        if User.query.filter((User.id == request.sid) | (User.userCode == msg['userCode'])).first() is None:

            # Add user to database based on teams lenght
            if User.query.filter_by(team=base_team).count() <= User.query.filter_by(team=base_team + 1).count():
                team = base_team
            else:
                team = base_team + 1
            add_teamMember(team, msg['username'], msg['userCode'])
            emit('message', {'username': msg['username'], 'team': team}, broadcast=True)

            # If there are more than 4 users, start the game and move all users to the play room.
            handle_start_game(user_count)
        else:
            send("userErrorMessage")
    except sqlalchemy.exc.IntegrityError:
        send("userErrorMessage")


def handle_start_game(user_count):
    user_count += 1
    if user_count == 4:
        send("startGameMessage", broadcast=True)
    elif user_count == 8:
        db.session.delete(Data.query.get('incomplete'))
        db.session.commit()
        emit('max_users_reached', str(user_count), broadcast=True)
        send("startGameMessage", to=request.sid, broadcast=False)
    elif user_count > 4:
        send("startGameMessage", to=request.sid, broadcast=False)


def retrieve_incomplete_team():
    if Data.query.get('incomplete') is None:
        base_team = math.floor(random.randint(0, 1000000) / 2) * 2
        while User.query.filter_by(team=base_team).count() > 0:
            base_team = math.floor(random.randint(0, 1000000) / 2) * 2
        user_count = 0
        db.session.add(Data(type='incomplete', value=str(base_team)))
        db.session.commit()
    else:
        base_team = int(Data.query.get('incomplete').value)
        user_count = User.query.filter((User.team == base_team) | (User.team == base_team + 1)).count()
    return base_team, user_count


# Socket.io function to add users to specific rooms
@socketio.on('join_room')
def add_to_room(msg):
    print("User " + msg['username'] + " joins!")
    user = User.query.get(msg['username'])
    if msg['rejoin'] == "True":
        emit('message', {'username': msg['username'], 'team': msg['team']}, broadcast=True)
    join_room(msg['team'])
    user.id = request.sid
    db.session.commit()


# Function to add users to the database
def add_teamMember(team, username, user_code):
    if User.query.filter((User.team == team) & User.drawer).count() == 0:
        new_user = User(id=request.sid, userCode=user_code, username=username, team=team, drawer=True, inGame=False,
                        cached=False)
    else:
        new_user = User(id=request.sid, userCode=user_code, username=username, team=team, drawer=False, inGame=False,
                        cached=False)
    db.session.add(new_user)
    db.session.commit()


# Function to get a random nous from static/words.txt
def get_random_noun():
    lines = open('static/words.txt').read().splitlines()
    return random.choice(lines).capitalize()


# Socket.io function to handle the guessing logic
@socketio.on('guess')
def validate_guess(msg):
    base_team = math.floor(msg['team'] / 2) * 2
    user = User.query.filter_by(id=request.sid).first()
    correct_team = None
    # Query the database for the current word to guess
    existing_word = Data.query.get('baseTeam' + str(base_team) + '_word').value
    # If the team guess is equal to the word in the database
    if msg['guess'].casefold() == existing_word.casefold():
        correct_team = msg['team']
        drawer = User.query.filter((User.team == correct_team) & (User.drawer == True)).first().username
        emit('game_over', {'user': user.username, 'team': correct_team, 'word': existing_word, 'winning_drawer': drawer}, room=str(base_team))
        emit('game_over', {'user': user.username, 'team': correct_team, 'word': existing_word, 'winning_drawer': drawer}, room=str(base_team+1))
    elif msg['guess'] == 'give_up':
        if msg['team'] == base_team:
            correct_team = base_team + 1
        else:
            correct_team = base_team
        emit('game_over', {'user': user.username, 'team': msg['team'], 'word': 'give_up'}, room=str(base_team))
        emit('game_over', {'user': user.username, 'team': msg['team'], 'word': 'give_up'}, room=str(base_team + 1))
    else:
        emit('add_word', msg['guess'], room=str(msg['team']))
    if correct_team is not None:
        # Reset the word and update score
        reset(correct_team)
        updateScore(correct_team, base_team)


# Function to update score based on the team
def updateScore(team, base_team):
    data_type = 'team' + str(team) + '_score'
    if Data.query.get(data_type) is None:
        db.session.add(Data(type=data_type, value="1"))
        score = '1'
    else:
        existing_score = Data.query.get(data_type)
        existing_score.value = str(int(existing_score.value) + 1)
        score = existing_score.value
    db.session.commit()
    score = int(score)
    # If score is 5 then restart the game
    if score == 5:
        delete_users(base_team)
        team = str(team % 2 + 1)
        emit('message', 'reset' + team, room=str(base_team))
        emit('message', 'reset' + team, room=str(base_team + 1))


# Function to reset the word to guess in the database
def reset(team):
    base_team = math.floor(team / 2) * 2
    word = Data.query.get('baseTeam' + str(base_team) + '_word')
    db.session.delete(word)
    team1 = User.query.filter((User.team == base_team) & (User.cached == False)).all()
    team2 = User.query.filter((User.team == base_team+1) & (User.cached == False)).all()
    drawer1_index = random.randint(0, len(team1)-1)
    drawer2_index = random.randint(0, len(team2)-1)
    find_new_drawer(team1, drawer1_index)
    find_new_drawer(team2, drawer2_index)
    db.session.commit()

def find_new_drawer(team, drawer_index):
    for i in range(0, len(team)):
        if team[i].drawer:
            team[i].drawer = False
            if i == drawer_index:
                if i == len(team)-1:
                    drawer_index = random.randint(0, len(team) - 2)
                    team[drawer_index].drawer = True
                else:
                    drawer_index = random.randint(i+1, len(team) - 1)
        elif i == drawer_index:
            team[i].drawer = True

def delete_users(base_team):
    for user in User.query.filter((User.team == base_team) | (User.team == base_team + 1)).all():
        db.session.delete(user)
        emit('delete_user', user.username, broadcast=True)
    items_to_delete = [Data.query.get('team' + str(base_team) + '_score'), Data.query.get('team' + str(base_team + 1) + '_score')]
    for item in items_to_delete:
        if item is not None:
            db.session.delete(item)
    db.session.commit()


@socketio.on('delete_user')
def delete_user(msg):
    print("Username to be deleted:" + msg['username'])
    user = User.query.get(msg['username'])
    if user is not None:
        leave_room(str(user.team))
        if msg['permanent'] == 'True':
            db.session.delete(user)
        else:
            user.cached = True
            print(msg['username'] + " cached " + str(user.cached))
        db.session.commit()
        base_team = math.floor(user.team / 2) * 2
        emit('delete_user', msg['username'], broadcast=True)
        if user.drawer and user.inGame:
            delete_users(base_team)
            emit('message', 'force_reset', room=str(base_team))
            emit('message', 'force_reset', room=str(base_team + 1))
            close_room(str(base_team))
            close_room(str(base_team + 1))



if __name__ == '__main__':
    db.drop_all()
    db.create_all()
    socketio.run(app)
