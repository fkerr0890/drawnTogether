from flask import Flask, render_template, request
from flask_socketio import SocketIO, send, join_room, leave_room

app = Flask(__name__)
app.config['SECRET_KEY'] = 'mysecret'
socketio = SocketIO(app, cors_allowed_origins='*')

users = []
team1 = []
team2 = []


@socketio.on('message')
def handleMessage(msg):
    print('Message: ' + msg)
    send(msg, broadcast=True)


@app.route("/")
def draw():
    return render_template("draw.html", team1=team1, team2=team2)


@app.route('/lobby')
def lobby():
    return render_template("index.html")


@socketio.on('joinUsername', namespace="/lobby")
def receive_username(username):
    print('Username: ' + username)
    send(username, broadcast=True)
    users.append({username: request.sid})
    if len(team1) <= len(team2):
        team1.append(username)
    else:
        team2.append(username)


if __name__ == '__main__':
    socketio.run(app)
