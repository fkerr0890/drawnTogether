# drawnTogether
This repository contains the source code for the DrawnTogether game as the final project for COMP446 at Macalester College.

Drawn Together is a team-based draw-and-guessing game where two teams compete to see who will win in 5 rounds by drawing a description and guessing as fast as they can. 
Each team has one drawer and at least one guesser. Drawers on both teams get the same word to draw and the guessers have to guess it as fast as possible. The team that guesses first gets a point. The game ends after 5 rounds. 

## How to run this project:

###1 Clone the GitHub repository
Clone this public [repository](https://github.com/LunguRadu/drawnTogether) on your local machine

###2 Make sure you have python3 installed

###3 Create a virtual environment for the project

Use this command to create a new virtual environment in the project folder `python3 -m venv <environemnt name>`

###4 Activate the virtual environed 

Use this command in the project folder to activate the virtual environment 
`source <your environemnt name>/bin/activate`


###5 Install project requirements 

<strong> Important: Make sure you do this step correctly. The project will only run with a specific set of packages mentioned in the requirements.txt folder!</strong>

Make sure that your virtual environment is active and run the following command
`pip install -r requirements.txt`


###5 Reset the database before you start 

Run `python3 reset_databse.py`. Make sure that you are in the `app` folder. 

###6 Run the application on the local environment

Run `python3 app.py`. Make sure that you are in the `app` folder. 

## How to play/test the game:

- Open 4 tabs separate tabs with the application
- Add 4 user in the 4 separate tabs
- The game will start after there are at least 4 users
- Add your guess in the guess field
- The game will run for 5 rounds

##References:

Flask-SocketIO: https://flask-socketio.readthedocs.io/en/latest/  
W3schools: https://www.w3schools.com/


