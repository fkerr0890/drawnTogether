import json
import random

import sqlalchemy.exc

from flask import Flask, render_template, request, session
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


@socketio.on('message')
def handleMessage(msg):
    send(msg, broadcast=True)


@app.route('/play/<username>')
def play(username):
    team1 = User.query.filter_by(team=0)
    team2 = User.query.filter_by(team=1)
    user = User.query.filter_by(username=username).first()
    try:
        word = get_random_noun()
        db.session.add(User(id=word, username='word'))
        db.session.commit()
    except sqlalchemy.exc.IntegrityError:
        db.session.rollback()
        word = User.query.filter_by(username='word').first().id

    return render_template("draw.html",
                           team1=team1,
                           team2=team2,
                           username=username,
                           drawer=user.drawer,
                           word_to_guess=word)


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
    lines = open('../static/words.txt').read().splitlines()
    return random.choice(lines).capitalize()


@socketio.on('guess')
def validate_guess(guess):
    existing_word = User.query.filter_by(username='word').first().id
    if guess.casefold() == existing_word.casefold():
        send('game_over', broadcast=True)


if __name__ == '__main__':
    socketio.run(app)
