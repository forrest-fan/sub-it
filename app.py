from flask import Flask, redirect, url_for, render_template, request
from werkzeug.utils import secure_filename
import pyrebase
import json
import model
import swap
import os
import shutil
import time
import datetime


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
    return redirect(url_for("dash"))

@app.route("/signin")
def signin():
    return render_template("signin.html")

@app.route("/handlesignin", methods=['GET', 'POST'])
def handlesignin():
    global user, userID, auth, db
    email = request.form['email']
    password = request.form['password']
    userID = auth.sign_in_with_email_and_password(email, password)['localId']
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
            data['weekly'] = [0, 0, 0, 0, 0, 0, 0]
        db.child('users').child(userID).update({'data': data})
    return user

@app.route("/handlesignout", methods=['GET', 'POST'])
def handlesignout():
    global user, auth
    print (user)
    if user is not None:
        print("signing out")
        user = None
        auth.current_user = None
        return ("Signed out successfully")
    raise Exception("Nobody is signed in")

@app.route("/signup")
def signup():
    return render_template("signup.html")

@app.route("/handlesignup", methods=['GET', 'POST'])
def handlesignup():
    global db, auth
    email = request.form['email']
    print(email)
    password = request.form['password']
    userID = auth.create_user_with_email_and_password(email, password)
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
    db.child("users").child(userID['localId']).set(userData)
    return userData

@app.route("/dashboard")
def dash():
    global user
    if user is not None:
        return render_template("index.html", user=user, auth=True)
    else:
        return render_template("index.html", user=None, auth=False)

@app.route("/setgoal", methods=['GET', 'POST'])
def setGoal():
    global db, user, userID
    newGoal = int(request.form['newGoal'])
    msg = db.child('users').child(userID).child('data').update({'dailyGoal': newGoal})
    user['data']['dailyGoal'] = newGoal
    return str(newGoal)

@app.route("/sub", methods=['GET', 'POST'])
def sub():
    global modelVar, user
    if user is not None:
        if request.method == 'POST':
            img = request.files['foodImg']
            filename = './static/img/upload' + img.filename
            img.save(filename)
            recipe = model.predict_class(modelVar, [filename], False)
            alternatives = swap.findAlts(recipe['ingredients'])
            return render_template("sub.html", user=user, auth=True, recipe=recipe, alts=alternatives)
        else:
            return render_template("sub.html", user=user, auth=True, recipe=None, alts=None)
    else:
        return render_template("sub.html", user=user, auth=False, recipe=None, alts=None)

@app.route("/handlesub", methods=['GET', 'POST'])
def handlesub():
    global user, userID, db, alt_ingr, ingr_co2
    userData = db.child('users').child(userID).child('data').get().val()
    totalSave = float(0)
    for key in request.form:
        initCO2 = ingr_co2[key]
        altCO2 = ingr_co2[request.form[key]]
        sub = {
            'food': key,
            'alternative': request.form[key],
            'savings': round(initCO2 - altCO2, 2),
            'time': int(time.time())
        }
        userData['history'].append(sub)
        totalSave += round(initCO2 - altCO2, 2)
    userData['weekly'][datetime.datetime.today().weekday()] += totalSave
    userData['dailyGoalAchieved'] += totalSave
    userData['subbed'] += totalSave
    user.data = userData
    db.child('users').child(userID).update({'data': userData})
    return str(totalSave)

@app.route("/history")
def history():
    global user, userID, db
    if user is not None:
        history = db.child('users').child(userID).child('data').child('history').get().val()
        return render_template("history.html", auth=True, history=history, user=user)
    else:
        return render_template("history.html", auth=False, history=None, user=None)

@app.template_filter('ctime')
def timectime(s):
    theTime = datetime.datetime.fromtimestamp(s)
    return theTime.strftime("%I:%M %p - %b %d %Y")

@app.template_filter('monthyr')
def monthyr(s):
    theTime = datetime.datetime.fromtimestamp(s)
    return theTime.strftime("%B %Y")

@app.route("/discover")
def discover():
    return render_template("discover.html")

@app.route("/about")
def about():
    return render_template("about.html")

if __name__ == "__main__":
    app.run(debug=True)