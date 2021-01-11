# modules
from flask import Flask, redirect, url_for, render_template, request
from werkzeug.utils import secure_filename
import pyrebase
import json
import os
import shutil
import time
import datetime

# model.py, swap.py, impact.py
import model
import swap
import comps

# Initialize firebase
firebaseConfig = {
    "apiKey": "AIzaSyD-kuTNL1EcxwnCgM4_0x9oyO_k7IdzATI",
    "authDomain": "sub-it-a29ca.firebaseapp.com",
    "databaseURL": "https://sub-it-a29ca-default-rtdb.firebaseio.com/",
    "projectId": "sub-it-a29ca",
    "storageBucket": "sub-it-a29ca.appspot.com",
    "messagingSenderId": "744036348319",
    "appId": "1:744036348319:web:8677ea4aeddccdda3fcdaa",
    "measurementId": "G-STLRB5PMY1"
}

# Firebase integration
firebase = pyrebase.initialize_app(firebaseConfig)
auth = firebase.auth()
user = None
userID = None
db = firebase.database()

# Build ML model
modelVar = model.buildModel()

# Open ingredients JSON
with open("./alt_ingr.json", 'r') as fp:
    alt_ingr = json.load(fp)

with open("./ingr_co2.json", 'r') as fp:
    ingr_co2 = json.load(fp)

app = Flask(__name__)

@app.route("/")
def home():
    # Redirect root to dashboard
    return redirect(url_for("dash"))

@app.route("/signin")
def signin():
    # Signin page
    return render_template("signin.html")

@app.route("/handlesignin", methods=['GET', 'POST'])
def handlesignin():
    global user, userID, auth, db
    # Extract email and password from HTML form
    email = request.form['email']
    password = request.form['password']

    # Sign in user firebase and store user ID
    userID = auth.sign_in_with_email_and_password(email, password)['localId']

    # Get user data from firebase realtime database
    user = db.child("users").child(userID).get().val()

    # reset daily/weekly data
    data = user['data']
    history = data['history']
    now = datetime.datetime.now()
    midnight =  now.replace(hour=0, minute=0, second=0, microsecond=0).timestamp()
    if len(history) > 1 and history[len(history) - 1]['time'] < midnight:
        # If most recent sub was yesterday, reset daily goal achieved to 0
        data['dailyGoalAchieved'] = 0
        if datetime.datetime.today().weekday() == 0:
            # if today is monday, then reset weekly data to all 0s
            # this only runs if no subs have been made today
            data['weekly'] = [0, 0, 0, 0, 0, 0, 0]
        db.child('users').child(userID).update({'data': data})
    return user

@app.route("/handlesignout", methods=['GET', 'POST'])
def handlesignout():
    global user, auth
    
    # If user is logged in, sign out user firebase
    if user is not None:
        print("signing out")
        user = None
        auth.current_user = None
        return ("Signed out successfully")
    raise Exception("Nobody is signed in")

@app.route("/signup")
def signup():
    # Sign up page
    return render_template("signup.html")

@app.route("/handlesignup", methods=['GET', 'POST'])
def handlesignup():
    global db, auth

    # Extract and password from HTML form
    email = request.form['email']
    password = request.form['password']

    # Create account in firebase and store userID
    userID = auth.create_user_with_email_and_password(email, password)

    # Initialize user data that will go into realtime database
    userData = {
        'data': {
            'history': {
                0: 0
            },
            'weekly': {
                0: 0,
                1: 0,
                2: 0,
                3: 0,
                4: 0,
                5: 0,
                6: 0
            },
            'dailyGoal': 0,
            'dailyGoalAchieved': 0,
            'joined': datetime.datetime.now.timestamp(),
            'subbed': 0
        },
        'email': email,
        'fname': request.form['fname'],
        'lname': request.form['lname']
    }

    # Update realtime database with new user data
    db.child("users").child(userID['localId']).set(userData)
    return userData

@app.route("/dashboard")
def dash():
    # Dashboard page
    global user
    if user is not None:
        return render_template("index.html", user=user)
    else:
        return render_template("index.html", user=None)

@app.route("/setgoal", methods=['GET', 'POST'])
def setGoal():
    # Set goal for new users
    global db, user, userID

    # Extract new goal from HTML form
    newGoal = int(request.form['newGoal'])

    # Update realtime database with new goal
    msg = db.child('users').child(userID).child('data').update({'dailyGoal': newGoal})
    user['data']['dailyGoal'] = newGoal
    return str(newGoal)

@app.route("/sub", methods=['GET', 'POST'])
def sub():
    global modelVar, user
    if user is not None:
        # If method is POST, then user is submitting image for processing
        if request.method == 'POST':
            recipe = {}
            alternatives = []
            print('post received')
            if request.form['recipeText'] == '':
                print('image')
                # Extract the image from HTML form
                img = request.files['foodImg']
                # Set filename and path for new image
                filename = './static/img/upload' + img.filename
                # Save the image
                img.save(filename)
                # Call prediction function using model.py
                recipe = model.predict_class(modelVar, [filename], False)
                # Find alternatives using swap.py
                alternatives = swap.findAlts(recipe['ingredients'])
            else:
                print('text')
                # Extract recipe from textbox
                recipe = {
                    'name': 'From Pasted Recipe',
                    'ingredients': request.form['recipeText'].splitlines(),
                    'image': 'favicon.png'
                }
                alternatives = swap.findAlts(recipe['ingredients'])
            return render_template("sub.html", user=user, recipe=recipe, alts=alternatives)
        else:
            return render_template("sub.html", user=user, recipe=None, alts=None)
    else:
        return render_template("sub.html", user=None, recipe=None, alts=None)

@app.route("/handlesub", methods=['GET', 'POST'])
def handlesub():
    global user, userID, db, alt_ingr, ingr_co2
    # Handle a new sub
    # Get user data from realtime database
    userData = db.child('users').child(userID).child('data').get().val()
    totalSave = float(0)
    for key in request.form:
        # For each food subbed, calculate the savings and add a dict to history in user data
        initCO2 = ingr_co2[key]
        altCO2 = ingr_co2[request.form[key]]
        sub = {
            'food': key,
            'alternative': request.form[key],
            'savings': round(initCO2 - altCO2, 2),
            'time': int(time.time())
        }
        userData['history'].append(sub)

        # Update total savings counter
        totalSave += round(initCO2 - altCO2, 2)
    # Update user data for daily goal, weekly data, and total subs
    userData['weekly'][datetime.datetime.today().weekday()] = round(userData['weekly'][datetime.datetime.today().weekday()] + totalSave, 2)
    userData['dailyGoalAchieved'] = round(userData['dailyGoalAchieved'] + totalSave, 2)
    userData['subbed'] = round(userData['subbed'] + totalSave, 2)
    user['data'] = userData

    # Push changes to realtime database
    db.child('users').child(userID).update({'data': userData})
    return str(totalSave)

@app.route("/history")
def history():
    global user, userID, db
    if user is not None:
        # Get the sub history from realtime database and render as table
        history = db.child('users').child(userID).child('data').child('history').get().val()
        return render_template("history.html", history=history, user=user)
    else:
        return render_template("history.html", history=None, user=None)

@app.template_filter('ctime')
def timectime(s):
    # JINJA filter for history.html to convert timestamp to HH:MM am/pm - Mon Day Year
    theTime = datetime.datetime.fromtimestamp(s)
    return theTime.strftime("%I:%M %p - %b %d %Y")

@app.template_filter('monthyr')
def monthyr(s):
    # JINJA filter for index.html to convert timestamp to Month Year
    theTime = datetime.datetime.fromtimestamp(s)
    return theTime.strftime("%B %Y")

@app.route("/impact")
def impact():
    # Impact page to show impact of all subs
    global user
    if user is not None:
        comparisons = comps.calculateImpact(user['data']['subbed'])
        return render_template("impact.html", user=user, comps=comparisons)
    else:
        return render_template("impact.html", user=None)

@app.route("/about")
def about():
    # Static about page as description of app
    return render_template("about.html")

if __name__ == "__main__":
    app.run(debug=True)