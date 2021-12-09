import json
import random

import sqlalchemy.exc

from flask import Flask, render_template, request, session, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_socketio import SocketIO, send, join_room, leave_room, emit

app = Flask(__name__)
app.config.from_pyfile('app.cfg')
socketio = SocketIO(app, cors_allowed_origins='*')
db = SQLAlchemy(app)


class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.String(200))
    username = db.Column(db.String(200), primary_key=True, nullable=False)
    team = db.Column(db.Integer)
    drawer = db.Column(db.Boolean)

    def __repr__(self):
        return self.username


class Data(db.Model):
    __tablename__ = 'data'
    type = db.Column(db.String(30), primary_key=True)
    value = db.Column(db.String(30), nullable=False)

    def __repr__(self):
        return self.value


@socketio.on('message')
def handleMessage(msg):
    send(msg, broadcast=True)


@app.route('/play/<username>')
def play(username):
    team1 = User.query.filter_by(team=0)
    team2 = User.query.filter_by(team=1)
    team1_score = 0 if Data.query.filter_by(type='team0_score').first() is None else Data.query.filter_by(type='team0_score').first().value
    team2_score = 0 if Data.query.filter_by(type='team1_score').first() is None else Data.query.filter_by(type='team1_score').first().value
    user = User.query.filter_by(username=username).first()
    try:
        word = get_random_noun()
        db.session.add(Data(type='word', value=word))
        db.session.commit()
    except sqlalchemy.exc.IntegrityError:
        db.session.rollback()
        word = Data.query.filter_by(type='word').first().value

    return render_template("draw.html",
                           team1=team1,
                           team2=team2,
                           username=username,
                           drawer=user.drawer,
                           team=user.team,
                           word_to_guess=word,
                           team1_score=team1_score,
                           team2_score=team2_score)


@app.route('/')
def lobby():
    return render_template("index.html", users=User.query.all())


@socketio.on('joinUsername', namespace="/lobby")
def receive_username(username):
    # Check that the user is not in the database already, according to sid

    try:
        if User.query.filter_by(id=request.sid).first() is None:
            len_team1 = User.query.filter_by(team=0).count()
            len_team2 = User.query.filter_by(team=1).count()
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

    if User.query.count() >= 4:
        send("startGameMessage", broadcast=True)


def add_teamMember(team, username, length):
    if length == 0:
        new_user = User(id=request.sid, username=username, team=team, drawer=True)
    else:
        new_user = User(id=request.sid, username=username, team=team, drawer=False)
    db.session.add(new_user)
    db.session.commit()


def get_random_noun():
    # url = "https://random-word-form.herokuapp.com/random/noun"
    # return requests.get(url).json()[0]
    lines = open('static/words.txt').read().splitlines()
    return random.choice(lines).capitalize()


@socketio.on('guess')
def validate_guess(msg):
    msg = json.loads(msg)
    existing_word = Data.query.filter_by(type='word').first().value
    if msg.get('guess').casefold() == existing_word.casefold():
        reset()
        updateScore(msg.get('team'))
        send('game_over', broadcast=True)


def updateScore(team):
    data_type = 'team' + str(team) + '_score'
    if Data.query.filter_by(type=data_type).first() is None:
        db.session.add(Data(type=data_type, value="1"))
        print(data_type + "1")
    else:
        existing_score = Data.query.get(data_type)
        existing_score.value = str(int(existing_score.value) + 1)
        print(data_type + existing_score.value)
    db.session.commit()


def reset():
    word = Data.query.get('word')
    db.session.delete(word)
    db.session.commit()


if __name__ == '__main__':
    socketio.run(app)
