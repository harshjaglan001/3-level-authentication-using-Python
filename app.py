from flask import Flask,request,render_template,session,redirect,flash
from flask_sqlalchemy import SQLAlchemy
from flask_mail import Mail, Message
import time, random
import bcrypt
import cv2
import numpy as np
import os

app = Flask(__name__)
app.secret_key = '3-FA-Secret-Key-365'
app.config["SQLALCHEMY_DATABASE_URI"] = 'sqlite:///database.db'
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 586
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USE_SSL'] = True
app.config['MAIL_USERNAME'] = 'hs762901@gmail.com'
app.config['MAIL_PASSWORD'] = '9996738636'  # Use an App Password here
mail = Mail(app)

db = SQLAlchemy(app)

def final_color(red_range, green_range, blue_range):
    # Ensure input values are within valid RGB range
    red = max(0, min(255, red_range))
    green = max(0, min(255, green_range))
    blue = max(0, min(255, blue_range))

    # Construct hexadecimal color code
    color_hex = "#{:02x}{:02x}{:02x}".format(red, green, blue)
    
    return color_hex

def generate_otp():
    return random.randint(100000, 999999)

def encode_faces(image):
    # Load pre-trained face detection model
    face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
    # Load pre-trained face recognition model
    face_recognizer = cv2.face.LBPHFaceRecognizer_create()

    # Load image
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    # Detect faces
    faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30))

    face_encodings = []
    for (x, y, w, h) in faces:
        face_roi = gray[y:y+h, x:x+w]
        face_encoding = face_recognizer.predict(face_roi)
        face_encodings.append(face_encoding)
    return face_encodings

class User(db.Model):
    username = db.Column(db.String(50), primary_key = True)
    email = db.Column(db.String(50), nullable = False)
    password = db.Column(db.String(100), nullable = False)
    color = db.Column(db.String(10), nullable = False)
    image = db.Column(db.LargeBinary, nullable = True)
    fingerprint = db.Column(db.LargeBinary, nullable = True)

    def __init__(self,username,email,password,image,color,fingerprint):
        self.email = email
        self.password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        self.username = username
        self.image = image
        self.color = color
        self.fingerprint = fingerprint

    def check_password(self,password):
        return bcrypt.checkpw(password.encode('utf-8'),self.password.encode('utf-8'))
    
    def check_color(self,color):
        return self.color == color

# Recreate the database
with app.app_context():
    db.drop_all()
    db.create_all()
    print("Database recreated.")

@app.route("/")
def home():  
    return render_template('home.html')

@app.route('/register', methods = ['GET','POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        image = request.form['image_data']
        color = request.form['color']

        face_encodings = None 
        '''# Encode faces
        if not image:
            face_encodings = encode_faces(image)'''
        
        if User.query.filter_by(username=username).first() is not None:
            return render_template('register.html',error = "User already exists")
        new_user = User(username,email,password,face_encodings,color,None)
        db.session.add(new_user)
        db.session.commit()

        return redirect('/login')

    return render_template('register.html')

@app.route('/login', methods = ['GET','POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        user = User.query.filter_by(username=username).first()

        if not user:
            return render_template('login.html', error='User not Registered!')
        elif not user.check_password(password):
            return render_template('login.html', error = 'Incorrect Password!')
        else:
            session['username'] = user.username
            session['email'] = user.email

        return redirect('/selection')
    return render_template('login.html')

@app.route('/selection', methods=['GET','POST'])
def selection():
    if request.method == 'POST' and session['username']:
        print(session['username'])
        return render_template('selection.html')
    return render_template('selection.html')

@app.route('/verify_color', methods = ['GET','POST'])
def verify_color():
    if request.method == 'POST' and session['username']:
        user = User.query.filter_by(username=session['username']).first()
        color = request.form['color']
        if user.check_color(color):
            return redirect('/send_otp')
        else:
            flash('Incorrect combination!')
    return render_template('color.html')

@app.route('/verify_face')
def verify_face():
    if request.method == 'POST' and session['username']:
        pass
    return render_template('face.html')

@app.route('/send_otp')
def send_otp():
    if session['username'] and session['email']:
        otp = generate_otp()
        session['otp'] = otp
        email = session['email']
        session['otp_time'] = time.time()

        # Send email
        msg = Message("Your OTP", sender=app.config['MAIL_USERNAME'], recipients=[email])
        msg.body = f"Your OTP is {otp}"
        mail.send(msg)

        flash("OTP sent to your email.")
        return redirect('/verify_otp')
    return render_template('selection.html', error = 'Action could not be completed!')


@app.route('/verify_otp', methods=['GET','POST'])
def verify_otp():
    if session['username'] and request.method == 'POST':
        user_otp = request.form['otp']
        if 'otp' in session and session['otp'] == int(user_otp):
            if time.time() - session['otp_time'] < 180:  # OTP is valid for 3 minutes
                flash("OTP Verified Successfully!")
                return redirect('/dashboard')
            else:
                flash("OTP expired. Please resend.")
        else:
            flash("Invalid OTP")
    return render_template('otp.html')

@app.route('/dashboard', methods=['GET','POST'])
def dashboard():
    if 'username' in session and 'email' in session:
        session.commit()
        return render_template('dashboard.html', username=session['username'], email=session['email'])
    else:
        return redirect('/login')
    
@app.route('/logout')
def logout():
    session.pop('username', None)
    session.pop('email', None)
    return redirect('/login')

if __name__ == '__main__':
    app.run(debug=True)