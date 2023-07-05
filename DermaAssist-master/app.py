from flask import Flask, request, render_template, session
import firebase_admin
from firebase_admin import credentials, auth, storage
from firebase_admin import firestore
import jinja2
from datetime import timedelta
import pyrebase
from flask import Flask, redirect, url_for, flash, session
from flask_session import Session
from PIL import Image
import numpy as np
import skin_cancer_detection as SCD
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email.utils import COMMASPACE
from email import encoders
import os
import PyPDF2
import random
import string
from twilio.rest import Client

app = Flask(__name__)
config = {
    "apiKey": "AIzaSyAR0XBuGC2yywq-q1DfQKfLl26LKk6l9K8",
  "authDomain": "fir-try-28f01.firebaseapp.com",
  "databaseURL": "https://fir-try-28f01-default-rtdb.firebaseio.com",
  "projectId": "fir-try-28f01",
  "storageBucket": "fir-try-28f01.appspot.com",
  "messagingSenderId": "588321601903",
  "appId": "1:588321601903:web:e072797fc9189e9465d09a",
  "measurementId": "G-04938M5W17"
}

cred = credentials.Certificate("serviceAccountKey.json")
firebase_admin.initialize_app(cred)
firebase = pyrebase.initialize_app(config)
auth = firebase.auth()
storage = firebase.storage()
db = firestore.client()
app.secret_key = 'abc'

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/getstarted', methods = ['GET', 'POST'])
def getstarted():
    return render_template('login.html')

@app.route('/login', methods = ['GET', 'POST'])
def login():
    if request.method == 'POST':
        global path_email
        path_email = request.form['email']
        password = request.form['password']
        user = None
        error = False
        if not path_email or not password:
            error = True
            flash('Please enter your email and password.')
        else:
            try:
                user = auth.sign_in_with_email_and_password(path_email, password)
            except auth.AuthError as e:
                # Handle any authentication errors
                error_code = e.detail.get('code')
                if error_code == 'EMAIL_NOT_FOUND':
                    error = True
                    flash('Invalid email address.')
                elif error_code == 'INVALID_PASSWORD':
                    error = True
                    flash('Invalid password.')
                else:
                    error = True
                    flash('An error occurred. Please try again later.')
        if user and not error:
            return render_template('dashboard.html')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    auth.logout()
    return redirect(url_for('index'))

@app.route('/dashboard')
def dashboard():
    return render_template("dashboard.html")

@app.route('/viewdoc', methods=['GET', 'POST'])
def viewdoc():
    doctor = []
    docs = db.collection('doctor').get()
    print(docs)
    for doc in docs:
        doctorsdictionary = doc.to_dict()
        doctor.append(doctorsdictionary)
    print(doctor)
    return render_template('view_doctors.html', doctor=doctor)

@app.route('/signup', methods = ['GET', 'POST'])
def signup():
    if request.method == 'POST':
        email = request.form['email']
        global first_name, last_name
        first_name = request.form['first_name']
        last_name = request.form['last_name']
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        data={
            first_name: {
                'First Name': first_name,
                'Email': email,
                'Last Name': last_name
            }
        }
        if password == confirm_password:
            user = auth.create_user_with_email_and_password(email, password)
            db.collection('pathologist').document(first_name).set(data)
            return render_template('login.html')
        elif auth.get_user_by_email(email) is not None:
            flash('Email already exists.')
        else:
            flash('Passwords do not match.')
    else:
        return render_template('signup.html')
    
@app.route('/doctor', methods = ['GET', 'POST'])
def doctor():
    if request.method == 'POST':
        
        global doctor_name
        global doctor_phone
        doctor_name = request.form['name']
        doctor_email = request.form['email']
        doctor_phone = request.form['contact']
        data = {
            doctor_name: {
                'name': doctor_name,
                'email': doctor_email,
                'phone': doctor_phone
            }
        }
        db.collection('doctor').document(doctor_name).set(data)
        session['doctor_name']= doctor_name
        session['doctor_email']= doctor_email
        session['doctor_phone']=doctor_phone
        return redirect(url_for('patient1'))
    return render_template('add_doc.html')

@app.route('/patient1', methods = ['GET', 'POST'])
def patient1():
    if request.method == 'POST':
        global patient_name
        global patient_email 
        global patient_phone
        doctor_name = request.form['doctor']
        patient_name = request.form['pname']
        patient_email = request.form['pemail']
        patient_phone = request.form['pcontact']

        data = {
            patient_name: {
                'name': patient_name,
                'email': patient_email,
                'phone': patient_phone
            }
        }
        db.collection('doctor').document(doctor_name).collection('patient').document(patient_name).set(data)
        session['doctor_name']= doctor_name
        session['patient_name']= patient_name
        session['patient_email']= patient_email
        session['patient_phone']=patient_phone
        return redirect(url_for('upload'))
    n = 0
    if n == 0:
        doclist = []
        doct = db.collection('doctor').get()
        for i in doct:
            doctors = i.to_dict()
            doclist.append(doctors)
        return render_template('add_patient1.html', doclist=doclist)

@app.route('/upload', methods = ['GET', 'POST'])
def upload():
    if request.method == 'POST':
        global file
        file = request.files['pic']
        if file:
            global result
            storage.child("images/" + file.filename).put(file)
            links=storage.child("images/" + file.filename).get_url(None)
            inputimg = Image.open(file)
            inputimg = inputimg.resize((28, 28))
            img = np.array(inputimg).reshape(-1, 28, 28, 3)
            result = SCD.model.predict(img)
            result = result.tolist()
            print(result)
            max_prob = max(result[0])
            class_ind = result[0].index(max_prob)
            print(class_ind)
            result = SCD.classes[class_ind]
            if class_ind == 0:
                info = "Actinic keratosis also known as solar keratosis or senile keratosis are names given to intraepithelial keratinocyte dysplasia. As such they are a pre-malignant lesion or in situ squamous cell carcinomas and thus a malignant lesion."
            elif class_ind == 1:
                info = "Basal cell carcinoma is a type of skin cancer. Basal cell carcinoma begins in the basal cells — a type of cell within the skin that produces new skin cells as old ones die off.Basal cell carcinoma often appears as a slightly transparent bump on the skin, though it can take other forms. Basal cell carcinoma occurs most often on areas of the skin that are exposed to the sun, such as your head and neck"
            elif class_ind == 2:
                info = "Benign lichenoid keratosis (BLK) usually presents as a solitary lesion that occurs predominantly on the trunk and upper extremities in middle-aged women. The pathogenesis of BLK is unclear; however, it has been suggested that BLK may be associated with the inflammatory stage of regressing solar lentigo (SL)1"
            elif class_ind == 3:
                info = "Dermatofibromas are small, noncancerous (benign) skin growths that can develop anywhere on the body but most often appear on the lower legs, upper arms or upper back. These nodules are common in adults but are rare in children. They can be pink, gray, red or brown in color and may change color over the years. They are firm and often feel like a stone under the skin. "
            elif class_ind == 4:
                info = "A melanocytic nevus (also known as nevocytic nevus, nevus-cell nevus and commonly as a mole) is a type of melanocytic tumor that contains nevus cells. Some sources equate the term mole with ‘melanocytic nevus’, but there are also sources that equate the term mole with any nevus form."
            elif class_ind == 5:
                info = "Pyogenic granulomas are skin growths that are small, round, and usually bloody red in color. They tend to bleed because they contain a large number of blood vessels. They’re also known as lobular capillary hemangioma or granuloma telangiectaticum."
            elif class_ind == 6:
                info = "Melanoma, the most serious type of skin cancer, develops in the cells (melanocytes) that produce melanin — the pigment that gives your skin its color. Melanoma can also form in your eyes and, rarely, inside your body, such as in your nose or throat. The exact cause of all melanomas isn't clear, but exposure to ultraviolet (UV) radiation from sunlight or tanning lamps and beds increases your risk of developing melanoma."
            session['result']=result
            return render_template("reults.html", result=result, info=info, links=links)
    return render_template('upload.html')

@app.route('/profile', methods = ['GET', 'POST'])
def profile():
        paths = db.collection('pathologist').get()
        patho = []
        for path in paths:
            pathsdictionary = path.to_dict()
            patho.append(pathsdictionary)
        print(patho)
        collection_ref = db.collection('pathologist')
        # Filter the collection by email
        query = collection_ref.where('Email', '==', path_email)
        records = query.get()
        record = records[0].to_dict()
        first_name = record.get('First Name')
        last_name = record.get('Last Name')
        session['first_name']=first_name
        session['last_name']=last_name
        return render_template('path_profile.html', path_email=path_email, first_name=first_name, last_name=last_name)

@app.route('/report', methods = ['GET', 'POST'])
def report():
    patient_name = session.get('patient_name')
    patient_email=session.get('patient_email')
    patient_phone=session.get('patient_phone')
    first_name=session.get('first_name')
    last_name=session.get('last_name')
    result=session.get('result')
    
    if request.method == 'POST':

        return render_template('mail.html')
    return render_template('report.html', patient_name=patient_name,  patient_email=patient_email, patient_phone=patient_phone, result=result, first_name=first_name, last_name=last_name)

newwebpage = os.path.join(os.getcwd(), "newwebpage.pdf")

@app.route('/mail', methods = ['GET', 'POST'])
def mail():
    if request.method == 'POST':
        given_phone = request.form['given_phone']
        password = ''.join(random.choices(string.ascii_letters + string.digits, k = 8))
        pdf_ref = storage.child("reports/newwebpage.pdf").download(filename = "newwebpage.pdf", path = ".")

        # Your Twilio account SID and auth token
        account_sid = "."
        auth_token = "."
        doctor_phone=session.get('patient_phone')
        # Create a Twilio client
        client = Client(account_sid, auth_token)
        
        # The phone number you want to send the message to
        to_number = doctor_phone

        # The Twilio phone number you want to use as the sender
        from_number = '+16205368988'

        # The message you want to send
        message = password

        # Send the message using Twilio
        client.messages.create(
                to = to_number,
                from_ = from_number,
                body = message)
        
        pdf_reader = PyPDF2.PdfReader(newwebpage)
        pdf_writer = PyPDF2.PdfWriter()
        pdf_writer.append_pages_from_reader(pdf_reader)
        pdf_writer.encrypt(password)
        encrypted_pdf_filename = "newwebpage_encrypted.pdf"
        with open(encrypted_pdf_filename, "wb") as pdf_file:
            pdf_writer.write(pdf_file)

        # Send the encrypted PDF file as an email attachment
        from_email = "dermassist.mail@gmail.com"
        from_password = "Dermassist@ASD"
        to_emails = ["aryaman.tiwary@somaiya.edu", "shriya.pingulkar@somaiya.edu"]
        subject = "Encrypted PDF file"
        message = "Here is the encrypted PDF file as requested."

        msg = MIMEMultipart()
        msg['From'] = from_email
        msg['To'] = COMMASPACE.join(to_emails)
        msg['Subject'] = subject
        msg.attach(MIMEText(message))

        with open(encrypted_pdf_filename, "rb") as pdf_file:
            attachment = MIMEBase('application', 'octet-stream')
            attachment.set_payload(pdf_file.read())
            encoders.encode_base64(attachment)
            attachment.add_header('Content-Disposition', f'attachment; filename="{encrypted_pdf_filename}"')
            msg.attach(attachment)
        smtp_server = "smtp.gmail.com"
        smtp_port = 587
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(from_email, from_password)
        server.sendmail(from_email, to_emails, msg.as_string())
        server.quit()
        os.remove(encrypted_pdf_filename)
        return render_template('final.html')
    return render_template('mail.html', result=result)

@app.route('/final', methods = ['GET', 'POST'])
def final():
    return render_template('final.html')
if __name__ == '__main__':
    app.run(debug = True)