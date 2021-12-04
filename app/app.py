import os

from flask import Flask, render_template, request
from flask_sqlalchemy import SQLAlchemy
from flask_socketio import SocketIO, send, join_room, leave_room, emit

app = Flask(__name__)
app.config.from_pyfile('app.cfg')
socketio = SocketIO(app, cors_allowed_origins='*')
db = SQLAlchemy(app)


# users = []
# team1 = []
# team2 = []


class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.String(200), primary_key=True)
    username = db.Column(db.String(200), nullable=False)
    team = db.Column(db.Integer, nullable=False)
    drawer = db.Column(db.Boolean)

    def __repr__(self):
        return 'Username: ' + self.username + ", Drawer: " + str(self.drawer)


@socketio.on('message')
def handleMessage(msg):
    send(msg, broadcast=True)


@app.route('/play/<username>')
def play(username):
    team1 = User.query.filter_by(team=0)
    team2 = User.query.filter_by(team=1)
    user = User.query.filter_by(username=username).first()
    print(user.drawer)
    return render_template("draw.html", team1=team1, team2=team2, username=username, drawer=user.drawer)


@app.route('/')
def lobby():
    return render_template("index.html")


@socketio.on('joinUsername', namespace="/lobby")
def receive_username(username):
    send(username, broadcast=True)
    len_team1 = User.query.filter_by(team=0).count()
    len_team2 = User.query.filter_by(team=1).count()
    if len_team1 <= len_team2:
        add_teamMember(0, username, len_team1)
    else:
        add_teamMember(1, username, len_team2)
    print("Lengths: " + str(len_team1) + ", " + str(len_team2))


def add_teamMember(team, username, length):
    if length == 0:
        new_user = User(id=request.sid, username=username, team=team, drawer=True)
    else:
        new_user = User(id=request.sid, username=username, team=team, drawer=False)
    db.session.add(new_user)
    db.session.commit()


if __name__ == '__main__':
    socketio.run(app)
