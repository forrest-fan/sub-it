from flask import Flask, redirect, url_for, render_template, request
from werkzeug.utils import secure_filename
import pyrebase
import json

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

firebase = pyrebase.initialize_app(firebaseConfig)
auth = firebase.auth()
user = None
userID = None

db = firebase.database()

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
            'joined': request.form['date'],
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
    if request.method == 'POST':
        img = request.files['foodImg']
        img.save('./files/' + secure_filename(img.filename))
        return render_template("sub.html")
    else:
        return render_template("sub.html")

# @app.route("/uploadImg")
# def uploadImg():
    

@app.route("/history")
def history():
    return render_template("history.html")

@app.route("/discover")
def discover():
    return render_template("discover.html")

@app.route("/rewards")
def rewards():
    return render_template("rewards.html")

@app.route("/profile")
def profile():
    global user
    if user is not None:
        return render_template("profile.html", user=user, auth=True)
    else:
        return render_template("profile.html", user="", auth=False)

if __name__ == "__main__":
    app.run(debug=True)