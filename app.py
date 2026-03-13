from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from flask_bcrypt import Bcrypt
import json
import csv
import os
from datetime import datetime, timedelta
import uuid
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from flask import g

app = Flask(__name__)
app.secret_key = "care4u_secret_key"
bcrypt = Bcrypt(app)

USERS_FILE = 'users.json'
DATASET_FILE = 'symptoms_dataset.csv'
REMINDERS_FILE = 'reminders.json'
HISTORY_FILE = 'medicine_history.json'
TRANSLATIONS_FILE = 'translations.json'
ALERTS_SENT_FILE = 'alerts_sent.json'
VITALS_FILE = 'vitals_history.json'

# Email Configuration (Replace with real credentials for production)
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
SMTP_USER = "your-email@gmail.com"
SMTP_PASS = "your-app-password"
EMAIL_FROM = "Care4U Alerts <your-email@gmail.com>"

def load_translations():
    if os.path.exists(TRANSLATIONS_FILE):
        with open(TRANSLATIONS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

TRANSLATIONS = load_translations()

SYMPTOMS_COLUMNS = [
    "username", "timestamp", "name", "gender", "age",
    "fever", "fever_value", "bp", "bp_value", "sugar", "sugar_value",
    "cough", "cough_level", "headache", "headache_level",
    "sore_throat", "sore_throat_level", "stomach_pain", "stomach_pain_level",
    "nausea", "nausea_level", "fatigue", "fatigue_level",
    "vomiting", "vomiting_level", "dizziness", "dizziness_level",
    "depression", "depression_level", "anxiety", "anxiety_level",
    "stress", "stress_level", "insomnia", "insomnia_level",
    "chest_pain", "chest_pain_level", "back_pain", "back_pain_level",
    "joint_pain", "joint_pain_level", "muscle_pain", "muscle_pain_level",
    "predicted_disease", "urgency", "symptoms", "verified_by", "verified_on"
]

def load_users():
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_users(users):
    with open(USERS_FILE, 'w') as f:
        json.dump(users, f, indent=4)

def append_symptoms_to_dataset(username, form, results):
    file_exists = os.path.isfile(DATASET_FILE)
    
    diseases = ", ".join([r['disease'] for r in results])
    urgency = "Low"
    if any(r.get('urgency') == 'High' for r in results): urgency = "High"
    elif any(r.get('urgency') == 'Medium' for r in results): urgency = "Medium"

    row = {
        "username": username,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "name": form.get("name"),
        "gender": form.get("gender"),
        "age": form.get("age"),
        "fever": "1" if form.get("high body temp") else "0",
        "fever_value": form.get("fever_value", ""),
        "bp": "1" if form.get("bp") else "0",
        "bp_value": form.get("bp_value", ""),
        "sugar": "1" if form.get("sugar") else "0",
        "sugar_value": form.get("sugar_value", ""),
        "cough": "1" if form.get("cough") else "0",
        "cough_level": form.get("cough_level", "0"),
        "headache": "1" if form.get("headache") else "0",
        "headache_level": form.get("headache_level", "0"),
        "sore_throat": "1" if form.get("sore_throat") else "0",
        "sore_throat_level": form.get("sore_throat_level", "0"),
        "stomach_pain": "1" if form.get("stomach_pain") else "0",
        "stomach_pain_level": form.get("stomach_pain_level", "0"),
        "nausea": "1" if form.get("nausea") else "0",
        "nausea_level": form.get("nausea_level", "0"),
        "fatigue": "1" if form.get("fatigue") else "0",
        "fatigue_level": form.get("fatigue_level", "0"),
        "vomiting": "1" if form.get("vomiting") else "0",
        "vomiting_level": form.get("vomiting_level", "0"),
        "dizziness": "1" if form.get("dizziness") else "0",
        "dizziness_level": form.get("dizziness_level", "0"),
        "depression": "1" if form.get("depression") else "0",
        "depression_level": form.get("depression_level", "0"),
        "anxiety": "1" if form.get("anxiety") else "0",
        "anxiety_level": form.get("anxiety_level", "0"),
        "stress": "1" if form.get("stress") else "0",
        "stress_level": form.get("stress_level", "0"),
        "insomnia": "1" if form.get("insomnia") else "0",
        "insomnia_level": "1" if form.get("insomnia_level") == "on" else "0", # Fix potential bug
        "chest_pain": "1" if form.get("chest_pain") else "0",
        "chest_pain_level": form.get("chest_pain_level", "0"),
        "back_pain": "1" if form.get("back_pain") else "0",
        "back_pain_level": form.get("back_pain_level", "0"),
        "joint_pain": "1" if form.get("joint_pain") else "0",
        "joint_pain_level": form.get("joint_pain_level", "0"),
        "muscle_pain": "1" if form.get("muscle_pain") else "0",
        "muscle_pain_level": form.get("muscle_pain_level", "0"),
        "predicted_disease": diseases,
        "urgency": urgency,
        "symptoms": ", ".join([s.replace("_", " ").title() for s in [
            "fever", "bp", "sugar", "cough", "headache", "sore_throat", 
            "stomach_pain", "nausea", "fatigue", "vomiting", "dizziness", 
            "chest_pain", "back_pain", "joint_pain", "muscle_pain"
        ] if row.get(s) == "1"])
    }

    with open(DATASET_FILE, 'a', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=SYMPTOMS_COLUMNS)
        if not file_exists:
            writer.writeheader()
        writer.writerow(row)

def predict_disease(form):
    matches = []
    
    # Extract symptoms and values
    cough_lv = int(form.get("cough_level", 0))
    fever_val = form.get("fever_value", "")
    vomit_lv = int(form.get("vomiting_level", 0))
    headache_lv = int(form.get("headache_level", 0))
    
    is_fever = form.get("high body temp")
    is_vomit = form.get("vomiting")
    is_cough = form.get("cough")
    is_headache = form.get("headache")
    is_stomach = form.get("stomach_pain")

    # Rule-based logic with Urgency
    if is_fever and is_cough:
        urg = "Medium"
        if "103" in fever_val or "104" in fever_val: urg = "High"
        matches.append({
            "disease": "Common Flu / Viral Infection",
            "medicines": ["Paracetamol", "Cough Syrup", "Vitamin C"],
            "symptoms": ["Fever", "Cough"],
            "urgency": urg,
            "percent": 85
        })

    if is_vomit and is_stomach:
        urg = "Medium"
        if vomit_lv > 7: urg = "High"
        matches.append({
            "disease": "Food Poisoning / Gastritis",
            "medicines": ["ORS", "Antacid", "Domperidone"],
            "symptoms": ["Vomiting", "Stomach Pain"],
            "urgency": urg,
            "percent": 80
        })

    if is_headache and int(form.get("stress_level", 0)) > 5:
        matches.append({
            "disease": "Tension Headache",
            "medicines": ["Aspirin", "Rest", "Hydration"],
            "symptoms": ["Headache", "Stress"],
            "urgency": "Low",
            "percent": 90
        })
    
    if form.get("chest_pain"):
        matches.append({
            "disease": "Potential Cardiac Concern / Angina",
            "medicines": ["Aspirin (if advised)", "Immediate Rest", "Call Emergency"],
            "symptoms": ["Chest Pain"],
            "urgency": "High",
            "percent": 95
        })

    if form.get("back_pain") or form.get("joint_pain"):
        urg = "Low"
        if int(form.get("back_pain_level", 0)) > 7 or int(form.get("joint_pain_level", 0)) > 7:
            urg = "Medium"
        matches.append({
            "disease": "Muscle Strain / Potential Arthritis",
            "medicines": ["Pain Relievers", "Warm Compress", "Physiotherapy"],
            "symptoms": ["Back/Joint Pain"],
            "urgency": urg,
            "percent": 75
        })

    if not matches:
        matches.append({
            "disease": "General Fatigue / Viral Prodrome",
            "medicines": ["Multivitamins", "Proper Sleep", "Healthy Diet"],
            "symptoms": ["Fatigue"],
            "urgency": "Low",
            "percent": 60
        })

    return matches

def get_reminders(username):
    if os.path.exists(REMINDERS_FILE):
        with open(REMINDERS_FILE, "r") as f:
            try:
                data = json.load(f)
                return data.get(username, [])
            except:
                return []
    return []

def save_reminders(username, reminders):
    data = {}
    if os.path.exists(REMINDERS_FILE):
        with open(REMINDERS_FILE, "r") as f:
            try:
                data = json.load(f)
            except:
                pass
    data[username] = reminders
    with open(REMINDERS_FILE, "w") as f:
        json.dump(data, f, indent=4)

def notify_trusted_individual(patient_name, trustee_email, trustee_name, reason):
    """
    Sends an email alert to the trusted contact.
    """
    subject = f"🚨 Care4U ALERT: {reason} for {patient_name}"
    body = f"""
    Dear {trustee_name},
    
    This is an automated emergency alert from Care4U.
    
    Patient: {patient_name}
    Event: {reason}
    Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
    
    Please check on them immediately or try to contact them.
    
    Best regards,
    Care4U Support Team
    """
    
    print(f"\n[EMAIL SIMULATION] To: {trustee_email}")
    print(f"[EMAIL SIMULATION] Subject: {subject}")
    print(f"[EMAIL SIMULATION] Body: {body.strip()}\n")

    # Real SMTP logic
    try:
        msg = MIMEMultipart()
        msg['From'] = EMAIL_FROM
        msg['To'] = trustee_email
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))

        # Only attempt real send if credentials are not placeholders
        if "your-email" not in SMTP_USER:
            with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
                server.starttls()
                server.login(SMTP_USER, SMTP_PASS)
                server.send_message(msg)
            print("✅ Real email sent successfully.")
        else:
            print("ℹ️ Email not sent: Update SMTP credentials in app.py to enable real alerts.")
            
    except Exception as e:
        print(f"❌ Failed to send email: {str(e)}")

def load_sent_alerts():
    if os.path.exists(ALERTS_SENT_FILE):
        with open(ALERTS_SENT_FILE, 'r') as f:
            try:
                return json.load(f)
            except:
                return {}
    return {}

def save_sent_alerts(alerts):
    with open(ALERTS_SENT_FILE, 'w') as f:
        json.dump(alerts, f, indent=4)

def check_missed_medications(username):
    users = load_users()
    user_data = users.get(username, {})
    
    if user_data.get("trustee_alerts") != "on" or not user_data.get("trustee_email"):
        return

    reminders = get_reminders(username)
    history = load_history(username)
    
    now = datetime.now()
    today_str = now.strftime("%Y-%m-%d")
    
    sent_alerts = load_sent_alerts()
    user_sent = sent_alerts.get(username, {})
    
    for r in reminders:
        try:
            r_time_parts = r["time"].split(":")
            r_hour = int(r_time_parts[0])
            r_min = int(r_time_parts[1]) if len(r_time_parts) > 1 else 0
            
            reminder_dt = now.replace(hour=r_hour, minute=r_min, second=0, microsecond=0)
            
            # If reminder was over 1 hour ago
            if reminder_dt < now and (now - reminder_dt).total_seconds() > 3600:
                # Check if already taken today
                taken = any(h["medicine"] == r["medicine"] and h["taken_at"].startswith(today_str) for h in history)
                
                if not taken:
                    # Check if alert already sent today for this medicine
                    last_sent = user_sent.get(r["medicine"])
                    if last_sent != today_str:
                        notify_trusted_individual(
                            user_data.get("name", username),
                            user_data["trustee_email"],
                            user_data.get("trustee_name", "Guardian"),
                            r["medicine"]
                        )
                        # Record alert sent
                        if username not in sent_alerts: sent_alerts[username] = {}
                        sent_alerts[username][r["medicine"]] = today_str
                        save_sent_alerts(sent_alerts)
        except Exception as e:
            print(f"Error checking missed meds: {e}")

def load_history(username):
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, 'r') as f:
            try:
                data = json.load(f)
                return data.get(username, [])
            except:
                return []
    return []

def save_history(username, history):
    data = {}
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, 'r') as f:
            try:
                data = json.load(f)
            except:
                pass
    data[username] = history
    with open(HISTORY_FILE, 'w') as f:
        json.dump(data, f, indent=4)

def get_health_streak(username):
    history = load_history(username)
    if not history:
        return 0
    
    # Get unique dates from history, sorted descending
    dates = sorted(list(set(h["taken_at"].split(" ")[0] for h in history)), reverse=True)
    if not dates:
        return 0
        
    now = datetime.now()
    today_str = now.strftime("%Y-%m-%d")
    yesterday_str = (now.replace(day=now.day-1) if now.day > 1 else now).strftime("%Y-%m-%d") # Simplified for streak logic
    
    # Check if the streak is still active (taken today or yesterday)
    if dates[0] != today_str and dates[0] != yesterday_str:
        # Check if yesterday calculation was correct (handle month boundaries better)
        from datetime import timedelta
        yesterday_str = (now - timedelta(days=1)).strftime("%Y-%m-%d")
        if dates[0] != yesterday_str:
            return 0

    streak = 0
    current_date = now
    
    # If not taken today, start checking from yesterday
    if dates[0] != today_str:
        current_date = now - timedelta(days=1)
    
    while True:
        date_str = current_date.strftime("%Y-%m-%d")
        if date_str in dates:
            streak += 1
            current_date -= timedelta(days=1)
        else:
            break
            
    return streak

def load_vitals(username):
    if os.path.exists(VITALS_FILE):
        with open(VITALS_FILE, 'r') as f:
            try:
                data = json.load(f)
                return data.get(username, [])
            except:
                return []
    return []

def save_vitals(username, vitals):
    data = {}
    if os.path.exists(VITALS_FILE):
        with open(VITALS_FILE, 'r') as f:
            try:
                data = json.load(f)
            except:
                pass
    data[username] = vitals
    with open(VITALS_FILE, 'w') as f:
        json.dump(data, f, indent=4)

@app.route("/")
def login_page():
    return render_template("Login.html")

@app.route("/signup", methods=["GET", "POST"])
def signup_page():
    if request.method == "POST":
        full_name = request.form.get("name")
        username = request.form.get("username")
        password = request.form.get("password")
        weight = request.form.get("weight", "")
        height = request.form.get("height", "")
        email = request.form.get("email", "")
        role = request.form.get("role", "patient")
        specialization = request.form.get("specialization", "")
        license_no = request.form.get("license", "")
        city = request.form.get("city", "")
        
        users = load_users()
        if username in users:
            return "User already exists!"
        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
        
        user_data = {
            "name": full_name,
            "password": hashed_password,
            "age": "",
            "gender": "",
            "blood_group": "",
            "weight": weight,
            "height": height,
            "email": email,
            "phone": phone,
            "city": city,
            "role": role,
            "email_alerts": "off",
            "sms_alerts": "off"
        }

        if role == 'doctor':
            user_data.update({
                "specialization": specialization,
                "license": license_no,
                "patients": []
            })
        else:
            user_data.update({
                "doctor_connected": None,
                "pending_doctor_request": None
            })

        user_data["joined_on"] = datetime.now().strftime("%b %Y")
        users[username] = user_data
        save_users(users)
        flash("Account created! Please login.")
        return redirect(url_for("login_page"))
    return render_template("Signup.html")


@app.route("/login", methods=["POST"])
def login():
    username = request.form.get("username")
    password = request.form.get("password")
    users = load_users()
    
    if username in users:
        user_data = users[username]
        stored_password = user_data["password"] if isinstance(user_data, dict) else user_data
        
        # Check if password matches (handling both hashed and legacy plain text)
        if stored_password.startswith('$2b$'):
            if bcrypt.check_password_hash(stored_password, password):
                session["user"] = username
                return redirect(url_for("dashboard_page"))
        else:
            # Legacy plain text check
            if stored_password == password:
                session["user"] = username
                return redirect(url_for("dashboard_page"))
            
    flash("Invalid username or password!")
    return redirect(url_for("login_page"))

@app.route("/logout")
def logout():
    session.pop("user", None)
    return redirect(url_for("login_page"))

@app.route("/forgot-password")
def forgot_password():
    return "Forgot password functionality is coming soon! Please contact support."

@app.before_request
def before_request():
    global TRANSLATIONS
    TRANSLATIONS = load_translations()
    lang = session.get('lang', 'en')
    g.lang = lang
    g.translations = TRANSLATIONS.get(lang, TRANSLATIONS.get('en', {}))

@app.context_processor
def inject_translations():
    def _(key):
        return g.translations.get(key, key)
    return dict(_=_, current_lang=g.lang)

@app.route("/set_language/<lang>")
def set_language(lang):
    if lang in TRANSLATIONS:
        session['lang'] = lang
    return redirect(request.referrer or url_for('dashboard_page'))

# --- Notification Helpers ---
def send_email_alert(recipient, subject, body):
    """Stub for Email Alerting using smtplib"""
    print(f"DEBUG: Attempting to send Email to {recipient}...")
    return True

def send_sms_alert(phone_number, message):
    """Stub for SMS Alerting (e.g. Twilio)"""
    print(f"DEBUG: Attempting to send SMS to {phone_number}: {message}")
    return True
# ---------------------------

@app.route("/dashboard")
def dashboard_page():
    if not session.get("user"):
        return redirect(url_for("login_page"))
    username = session.get("user")
    check_missed_medications(username)
    users = load_users()
    user_data = users.get(username, {})
    
    if user_data.get("role") == "doctor":
        # Load patient details for connected patients
        patient_usernames = user_data.get("patients", [])
        patients = []
        for p_username in patient_usernames:
            if p_username in users:
                p_data = users[p_username]
                p_data["username"] = p_username
                patients.append(p_data)
        
        # Load pending requests
        pending_requests = []
        for uname, udata in users.items():
            if udata.get("pending_doctor_request") == username:
                udata["username"] = uname
                pending_requests.append(udata)
                
        return render_template("DoctorDashboard.html", user_data=user_data, username=username, patients=patients, pending_requests=pending_requests)
    
    # Get recent history
    history = []
    if os.path.exists(DATASET_FILE):
        with open(DATASET_FILE, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row.get("username") == username:
                    # Fix missing symptoms list for old records
                    if not row.get("symptoms"):
                        s_list = [s.replace("_", " ").title() for s in [
                            "fever", "bp", "sugar", "cough", "headache", "sore_throat", 
                            "stomach_pain", "nausea", "fatigue", "vomiting", "dizziness", 
                            "chest_pain", "back_pain", "joint_pain", "muscle_pain"
                        ] if row.get(s) == "1"]
                        row["symptoms"] = ", ".join(s_list)
                    history.append(row)
    
    recent_assessments = history[-3:] if history else []
    recent_assessments.reverse()
    
    # Get upcoming reminders
    all_reminders = get_reminders(username)
    upcoming_reminders = all_reminders[:3] # Simplified for now
    
    # Calculate health streak
    streak = get_health_streak(username)
    
    # Get latest vitals for dashboard display
    vitals = load_vitals(username)
    latest_vitals = vitals[-1] if vitals else {}
    
    # Analyze symptom trend
    trend_warning = analyze_symptom_trend(username)
    
    return render_template("Dashboard.html", 
                         username=username, 
                         user_data=user_data, 
                         recent_assessments=recent_assessments,
                         upcoming_reminders=upcoming_reminders,
                         streak=streak,
                         latest_vitals=latest_vitals,
                         trend_warning=trend_warning)

@app.route("/symptoms")
def symptoms_page():
    if not session.get("user"):
        return redirect(url_for("login_page"))
    username = session.get("user")
    users = load_users()
    user_data = users.get(username, {})
    return render_template("Symptoms.html", username=username, user_data=user_data)

@app.route("/predict", methods=["POST"])
def disease_page():
    if not session.get("user"):
        return redirect(url_for("login_page"))
    username = session.get("user")
    results = predict_disease(request.form)
    users = load_users()
    user_data = users.get(username, {})
    return render_template("Disease.html", results=results, username=username, user_data=user_data)

@app.route("/history", methods=["GET"])
def history_page():
    if not session.get("user"):
        return redirect(url_for("login_page"))
    username = session.get("user")
    history = []
    if os.path.exists(DATASET_FILE):
        with open(DATASET_FILE, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row.get("username") == username:
                    # Fix missing symptoms list for old records
                    if not row.get("symptoms"):
                        s_list = [s.replace("_", " ").title() for s in [
                            "fever", "bp", "sugar", "cough", "headache", "sore_throat", 
                            "stomach_pain", "nausea", "fatigue", "vomiting", "dizziness", 
                            "chest_pain", "back_pain", "joint_pain", "muscle_pain"
                        ] if row.get(s) == "1"]
                        row["symptoms"] = ", ".join(s_list)
                    history.append(row)
    history.reverse()
    users = load_users()
    user_data = users.get(username, {})
    return render_template("History.html", history=history, username=username, user_data=user_data)

@app.route("/reminders")
def reminders_page():
    if not session.get("user"):
        return redirect(url_for("login_page"))
    username = session.get("user")
    check_missed_medications(username)
    reminders = get_reminders(username)
    users = load_users()
    user_data = users.get(username, {})
    return render_template("Reminders.html", reminders=reminders, username=username, user_data=user_data)

@app.route("/add_reminder", methods=["POST"])
def add_reminder():
    if not session.get("user"):
        return redirect(url_for("login_page"))
    username = session.get("user")
    medicine = request.form.get("medicine")
    rem_times = request.form.get("reminder_time") # Can be "HH:MM" or "HH:MM, HH:MM"
    
    if medicine and rem_times:
        # Split by comma and strip whitespace
        time_list = [t.strip() for t in rem_times.split(',') if t.strip()]
        reminders = get_reminders(username)
        
        for t in time_list:
            reminders.append({
                "id": str(uuid.uuid4()),
                "medicine": medicine,
                "time": t,
                "created_at": datetime.now().strftime("%Y-%m-%d %H:%M")
            })
        save_reminders(username, reminders)
        
    return redirect(url_for("reminders_page"))

@app.route("/mark_taken/<reminder_id>", methods=["POST"])
def mark_taken(reminder_id):
    if not session.get("user"):
        return redirect(url_for("login_page"))
    username = session.get("user")
    reminders = get_reminders(username)
    
    reminder = next((r for r in reminders if r["id"] == reminder_id), None)
    if reminder:
        history = load_history(username)
        history.append({
            "id": reminder["id"],
            "medicine": reminder["medicine"],
            "scheduled_time": reminder["time"],
            "taken_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })
        save_history(username, history)
        
    return redirect(url_for("reminders_page"))

@app.route("/calendar")
def calendar_page():
    if not session.get("user"):
        return redirect(url_for("login_page"))
    username = session.get("user")
    reminders = get_reminders(username)
    history = load_history(username)
    users = load_users()
    user_data = users.get(username, {})
    return render_template("Calendar.html", reminders=reminders, history=history, username=username, user_data=user_data)

@app.route("/profile", methods=["GET", "POST"])
def profile_page():
    if not session.get("user"):
        return redirect(url_for("login_page"))
    username = session.get("user")
    users = load_users()
    user_data = users.get(username, {})

    if request.method == "POST":
        user_data["name"] = request.form.get("name")
        user_data["age"] = request.form.get("age")
        user_data["gender"] = request.form.get("gender")
        user_data["blood_group"] = request.form.get("blood_group")
        user_data["weight"] = request.form.get("weight")
        user_data["height"] = request.form.get("height")
        user_data["email"] = request.form.get("email")
        user_data["phone"] = request.form.get("phone")
        user_data["city"] = request.form.get("city")
        user_data["trustee_name"] = request.form.get("trustee_name", "")
        user_data["trustee_email"] = request.form.get("trustee_email", "")
        user_data["trustee_phone"] = request.form.get("trustee_phone", "")
        user_data["trustee_alerts"] = "on" if request.form.get("trustee_alerts") else "off"
        user_data["email_alerts"] = "on" if request.form.get("email_alerts") else "off"
        user_data["sms_alerts"] = "on" if request.form.get("sms_alerts") else "off"
        
        # Handle Role-specific fields
        if user_data.get('role') == 'doctor':
            user_data["specialization"] = request.form.get("specialization", "")
            user_data["license"] = request.form.get("license", "")
        
        # Handle password update
        new_password = request.form.get("password")
        if new_password:
            user_data["password"] = bcrypt.generate_password_hash(new_password).decode('utf-8')
        
        users[username] = user_data
        save_users(users)
        flash("Profile updated successfully!")
        return redirect(url_for("profile_page"))

    return render_template("Profile.html", user_data=user_data, username=username)

@app.route("/connect_doctor", methods=["POST"])
def connect_doctor():
    if not session.get("user"):
        return {"success": False, "error": "Unauthorized"}, 401
    
    data = request.json
    doctor_username = data.get("doctor_username")
    patient_username = session.get("user")
    
    users = load_users()
    if doctor_username not in users:
        return {"success": False, "error": "Doctor not found"}
    
    doctor_data = users[doctor_username]
    if doctor_data.get("role") != "doctor":
        return {"success": False, "error": "User is not a doctor"}
    
    # Set pending request
    patient_data = users[patient_username]
    patient_data["pending_doctor_request"] = doctor_username
    
    save_users(users)
    return {"success": True}

@app.route("/approve_patient/<patient_username>")
def approve_patient(patient_username):
    if not session.get("user"):
        return redirect(url_for("login_page"))
    
    doctor_username = session.get("user")
    users = load_users()
    doctor_data = users.get(doctor_username)
    
    if not doctor_data or doctor_data.get("role") != "doctor":
        return redirect(url_for("dashboard_page"))
    
    patient_data = users.get(patient_username)
    if patient_data and patient_data.get("pending_doctor_request") == doctor_username:
        # Connect
        patient_data["doctor_connected"] = doctor_username
        patient_data["pending_doctor_request"] = None
        
        if "patients" not in doctor_data:
            doctor_data["patients"] = []
        if patient_username not in doctor_data["patients"]:
            doctor_data["patients"].append(patient_username)
            
        save_users(users)
        flash(f"Approved connection with {patient_username}")
        
    return redirect(url_for("dashboard_page"))

@app.route("/decline_patient/<patient_username>")
def decline_patient(patient_username):
    if not session.get("user"):
        return redirect(url_for("login_page"))
    
    doctor_username = session.get("user")
    users = load_users()
    patient_data = users.get(patient_username)
    
    if patient_data and patient_data.get("pending_doctor_request") == doctor_username:
        patient_data["pending_doctor_request"] = None
        save_users(users)
        flash(f"Declined connection with {patient_username}")
        
    return redirect(url_for("dashboard_page"))

@app.route("/disconnect_doctor")
def disconnect_doctor():
    if not session.get("user"):
        return redirect(url_for("login_page"))
    
    patient_username = session.get("user")
    users = load_users()
    patient_data = users.get(patient_username)
    
    if patient_data and patient_data.get("doctor_connected"):
        doctor_username = patient_data["doctor_connected"]
        doctor_data = users.get(doctor_username)
        if doctor_data and "patients" in doctor_data:
            if patient_username in doctor_data["patients"]:
                doctor_data["patients"].remove(patient_username)
        
        patient_data["doctor_connected"] = None
        save_users(users)
        flash("Disconnected from doctor.")
        
    return redirect(url_for("profile_page"))

@app.route("/find_doctors")
def find_doctors():
    if not session.get("user"):
        return redirect(url_for("login_page"))
    
    username = session.get("user")
    users = load_users()
    user_data = users.get(username, {})
    
    search_city = request.args.get("city", "").strip()
    search_spec = request.args.get("spec", "").strip()
    
    # Filter doctors
    all_doctors = [
        {"username": uname, **udata} 
        for uname, udata in users.items() 
        if udata.get("role") == "doctor"
    ]
    
    filtered_doctors = []
    for dr in all_doctors:
        match_city = not search_city or search_city.lower() in dr.get("city", "").lower()
        match_spec = not search_spec or search_spec.lower() in dr.get("specialization", "").lower()
        
        if match_city and match_spec:
            filtered_doctors.append(dr)
            
    # Sort: nearest first if no search city is specified
    if not search_city and user_data.get("city"):
        user_city = user_data.get("city").lower()
        filtered_doctors.sort(key=lambda x: x.get("city", "").lower() != user_city)

    return render_template(
        "FindDoctors.html", 
        doctors=filtered_doctors, 
        user_city=user_data.get("city", ""),
        search_city=search_city,
        search_spec=search_spec,
        connected_doctor=user_data.get("doctor_connected"),
        user_data=user_data,
        username=username
    )
def hospitals_page():
    if not session.get("user"):
        return redirect(url_for("login_page"))
    username = session.get("user")
    users = load_users()
    user_data = users.get(username, {})
    return render_template("Hospitals.html", username=username, user_data=user_data)

@app.route("/about")
def about_page():
    username = session.get("user")
    users = load_users()
    user_data = users.get(username, {})
    return render_template("AboutUs.html", username=username, user_data=user_data)

@app.route("/stats")
def stats_page():
    if not session.get("user"):
        return redirect(url_for("login_page"))
    username = session.get("user")
    history = []
    if os.path.exists(DATASET_FILE):
        with open(DATASET_FILE, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row.get("username") == username:
                    # Clean data: DictReader might have 'None' keys if columns mismatch
                    clean_row = {str(k): v for k, v in row.items() if k is not None}
                    history.append(clean_row)
    users = load_users()
    user_data = users.get(username, {})
    vitals = load_vitals(username)
    return render_template("Stats.html", history=history, vitals=vitals, username=username, user_data=user_data)

@app.route("/delete_reminder/<reminder_id>", methods=["POST"])
def delete_reminder(reminder_id):
    if not session.get("user"):
        return redirect(url_for("login_page"))
    username = session.get("user")
    reminders = get_reminders(username)
    reminders = [r for r in reminders if r["id"] != reminder_id]
    save_reminders(username, reminders)
    return redirect(url_for("reminders_page"))

@app.route("/api/watch/sync")
def watch_sync_api():
    if not session.get("user"):
        return {"success": False, "message": "Unauthorized"}, 401
    
    username = session.get("user")
    reminders = get_reminders(username)
    
    # Return a simplified object for smartwatch consumption
    sync_data = {
        "user": username,
        "timestamp": datetime.now().isoformat(),
        "reminders": [
            {
                "id": r["id"],
                "medicine": r["medicine"],
                "time": r["time"]
            } for r in reminders
        ]
    }
    return sync_data

@app.route("/manifest.json")
def serve_manifest():
    return app.send_static_file("manifest.json")

@app.route("/sw.js")
def serve_sw():
    return app.send_static_file("sw.js")

@app.route("/view_patient/<patient_username>")
def view_patient(patient_username):
    if not session.get("user"):
        return redirect(url_for("login_page"))
    
    doctor_username = session.get("user")
    users = load_users()
    doctor_data = users.get(doctor_username)
    
    if doctor_data.get("role") != "doctor":
        return redirect(url_for("dashboard_page"))
    
    if patient_username not in doctor_data.get("patients", []):
        flash("You are not connected to this patient.")
        return redirect(url_for("dashboard_page"))
        
    patient_data = users.get(patient_username, {})
    
    # Load patient history
    # For now, we reuse the history logic from dashboard
    history = []
    if os.path.exists(DATASET_FILE):
        with open(DATASET_FILE, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row["username"] == patient_username:
                    history.append(row)
    
    history = history[::-1] # Recent first
    
    return render_template("History.html", user_data=patient_data, username=patient_username, history=history, is_doctor=True)

@app.route("/verify_prediction", methods=["POST"])
def verify_prediction():
    if not session.get("user"):
        return {"success": False, "error": "Unauthorized"}, 401
    
    doctor_username = session.get("user")
    data = request.json
    patient_username = data.get("patient_username")
    timestamp = data.get("timestamp")
    
    users = load_users()
    if users.get(doctor_username, {}).get("role") != "doctor":
        return {"success": False, "error": "Only doctors can verify predictions"}
    
    # Update CSV by reading all and rewriting with modification
    updated_rows = []
    found = False
    
    if os.path.exists(DATASET_FILE):
        with open(DATASET_FILE, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            fieldnames = SYMPTOMS_COLUMNS
            for row in reader:
                if row["username"] == patient_username and row["timestamp"] == timestamp:
                    row["verified_by"] = doctor_username
                    row["verified_on"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    found = True
                updated_rows.append(row)
        
        if found:
            with open(DATASET_FILE, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=SYMPTOMS_COLUMNS)
                writer.writeheader()
                writer.writerows(updated_rows)
            return {"success": True}
    
    return {"success": False, "error": "Record not found"}

@app.route("/log_vitals", methods=["POST"])
def log_vitals():
    if not session.get("user"):
        return redirect(url_for("login_page"))
    
    username = session.get("user")
    vitals = load_vitals(username)
    
    new_entry = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "bp": request.form.get("bp"),
        "sugar": request.form.get("sugar"),
        "weight": request.form.get("weight"),
        "temp": request.form.get("temp")
    }
    
    vitals.append(new_entry)
    save_vitals(username, vitals)
    flash("Vitals logged successfully!")
    return redirect(url_for("dashboard_page"))

def analyze_symptom_trend(username):
    """
    Analyzes the last 5 symptom assessments to detect worsening trends.
    Returns True if symptoms are getting significantly worse.
    """
    history = []
    if os.path.exists(DATASET_FILE):
        with open(DATASET_FILE, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row.get("username") == username:
                    history.append(row)
    
    if len(history) < 3:
        return False # Need at least 3 assessments to see a trend
        
    def calculate_score(record):
        score = 0
        # Symptoms that have intensity levels
        levels = [
            "cough_level", "headache_level", "sore_throat_level", 
            "stomach_pain_level", "nausea_level", "fatigue_level", 
            "vomiting_level", "dizziness_level", "chest_pain_level",
            "back_pain_level", "joint_pain_level", "muscle_pain_level"
        ]
        for l in levels:
            val = record.get(l, "0")
            try:
                if val and str(val).strip().isdigit():
                    score += int(val)
            except (ValueError, TypeError):
                pass
            
        # Urgency weight
        urg = record.get("urgency", "Low")
        if urg == "High": score += 10
        elif urg == "Medium": score += 5
        
        # Fever weight
        if record.get("fever") == "1":
            score += 5
            
        return score

    # Get scores for last 5 records
    scores = [calculate_score(r) for r in history[-5:]]
    
    if len(scores) < 3: return False
    
    # Compare last 2 assessments vs previous 3 (or whatever is available)
    recent_mean = sum(scores[-2:]) / 2
    previous_mean = sum(scores[:-2]) / len(scores[:-2]) if len(scores) > 2 else scores[0]
    
    # If recent mean is 30% higher than previous, trigger warning
    if recent_mean > (previous_mean * 1.3) and recent_mean > 5:
        return True
        
    return False

@app.route("/trigger_sos", methods=["POST"])
def trigger_sos():
    if not session.get("user"):
        return {"success": False, "error": "Unauthorized"}, 401
    
    username = session.get("user")
    users = load_users()
    user_data = users.get(username, {})
    
    trustee_email = user_data.get("trustee_email")
    trustee_name = user_data.get("trustee_name", "Guardian")
    
    if not trustee_email:
        return {"success": False, "error": "No trustee email configured in profile"}
    
    # Trigger the notification
    notify_trusted_individual(
        user_data.get("name", username),
        trustee_email,
        trustee_name,
        "EMERGENCY SOS ALERT"
    )
    
    return {"success": True}

if __name__ == "__main__":
    app.run(debug=True)