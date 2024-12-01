from flask import Flask
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///app.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'ihaterishabh7890'
db = SQLAlchemy(app)
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    role = db.Column(db.String(10), nullable=False)  # admin, doctor, or customer
class Sales(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    amount = db.Column(db.Float, nullable=False)  # Amount of the sale
    timestamp = db.Column(db.DateTime, default=db.func.current_timestamp())
    
class Receipt(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    status = db.Column(db.String(20), default="pending")
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    address = db.Column(db.String(200), nullable=False)
    symptoms = db.Column(db.String(300), nullable=False)  # Comma-separated string
    additional_symptoms = db.Column(db.String(300), nullable=True)
    daily_life_impact = db.Column(db.Integer, nullable=False)
    previous_treatment = db.Column(db.Integer, nullable=False)  # 1 = Yes, 0 = No
    symptom_duration = db.Column(db.String(50), nullable=False)




# Create all tables
with app.app_context():
    
    db.create_all()
    existing_admin = User.query.filter_by(email='admin@email.com').first()

    if not existing_admin:
        # If admin doesn't exist, create a new one with a hashed password
        admin = User(email='admin@email.com', password='admin', role="admin")

        # Add the admin user to the session and commit
        db.session.add(admin)
        db.session.commit()
        print("Admin user created!")

from functools import wraps
from flask import flash, redirect, render_template, request, jsonify, session, url_for
from app import app, db, User, Receipt, Sales

# Helper function to fetch user by email

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))  # Redirect to the login page if not logged in
        return f(*args, **kwargs)
    return decorated_function


def admin_login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('admin_login'))  # Redirect to the login page if not logged in
        return f(*args, **kwargs)
    return decorated_function

def get_user(email):
    return User.query.filter_by(email=email).first()

# # Admin Endpoints
# @app.route('/admin/add_doctor', methods=['POST'])
# def add_doctor():
#     data = request.json
#     new_user = User(email=data['email'], password=data['password'], role='doctor')
#     db.session.add(new_user)
#     db.session.commit()
#     return jsonify({"message": "Doctor added successfully"}), 201

# Admin Dashboard Routes
@app.route('/admin/add_sales', methods=['GET', 'POST'])
def add_sales():
    if request.method == 'POST':
        amount = request.form['amount']
        new_sale = Sales(amount=amount)
        db.session.add(new_sale)
        db.session.commit()
        flash('Sale added successfully!', 'success')
        return redirect(url_for('view_sales'))
    return render_template('add_sales.html')

@app.route('/admin/view_sales', methods=['GET'])
def view_sales():
    total_sales = db.session.query(db.func.sum(Sales.amount)).scalar() or 0
    return render_template('view_sales.html', total_sales=total_sales)

@app.route('/admin/add_doctor', methods=['GET', 'POST'])
def add_doctor():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        new_doctor = User(email=email, password=password, role='doctor')
        db.session.add(new_doctor)
        db.session.commit()
        flash('Doctor added successfully!', 'success')
        return redirect(url_for('view_doctors'))
    return render_template('add_doctor.html')

@app.route('/admin/view_doctors', methods=['GET'])
def view_doctors():
    doctors = User.query.filter_by(role='doctor').all()
    return render_template('view_doctors.html', doctors=doctors)

@app.route('/admin/all_receipts', methods=['GET'])
def all_receipts():
    receipts = Receipt.query.all()
    return render_template('view_receipts.html', receipts=receipts)

@app.route('/admin/revenue', methods=['GET'])
def admin_revenue():
    doctor_id = request.args.get('doctor_id')
    receipts = Receipt.query.filter_by(doctor_id=doctor_id, status="approved").all()
    total_revenue = sum(receipt.price for receipt in receipts)
    return jsonify({"total_revenue": total_revenue}), 200


# Doctor Endpoints
def is_doctor():
    user_id = session.get('user_id')
    if not user_id:
        return False
    user = User.query.get(user_id)
    return user and user.role == 'doctor'

@app.route('/doctor/login', methods=['GET', 'POST'])
def doctor_login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        # Authenticate user
        user = User.query.filter_by(email=email).first()
        if user and user.password == password and user.role == 'doctor':  # Add hashing in production
            session['user_id'] = user.id
            session['role'] = 'doctor'
            flash('Login successful!', 'success')
            return redirect(url_for('doctor_dashboard'))

        flash('Invalid credentials or you are not a doctor.', 'error')
        return render_template('doctor_login.html')

    return render_template('doctor_login.html')


@app.route('/doctor/dashboard')
@login_required
def doctor_dashboard():
    if not is_doctor():
        flash('Access denied. Please log in as a doctor.', 'error')
        return redirect(url_for('doctor_login'))

    # Fetch pending receipts for the doctor
    doctor_id = session.get('user_id')
        # Fetch previous receipts (approved or rejected)
    pending_receipts = Receipt.query.filter(Receipt.status == "pending").all()
    
    previous_receipts = Receipt.query.filter(Receipt.status != "pending").all()

    return render_template('doctor_dashboard.html', 
                           pending_receipts=pending_receipts, 
                           previous_receipts=previous_receipts)


@app.route('/doctor/approve_reject_receipt', methods=['POST'])
def approve_reject_receipt():
    if not is_doctor():
        return jsonify({"error": "Unauthorized"}), 403

    data = request.json
    receipt_id = data.get('receipt_id')
    new_status = data.get('status')  # "approved" or "rejected"

    receipt = Receipt.query.get(receipt_id)
    if not receipt:
        return jsonify({"error": "Receipt not found or not authorized"}), 404

    receipt.status = new_status
    db.session.commit()

    return jsonify({"message": f"Receipt {new_status} successfully."}), 200
@app.route('/doctor/patient_receipts', methods=['GET'])
def patient_receipts():
    doctor_id = request.args.get('doctor_id')
    patient_id = request.args.get('patient_id')
    receipts = Receipt.query.filter_by(doctor_id=doctor_id, customer_id=patient_id).all()
    return jsonify([receipt.to_dict() for receipt in receipts]), 200

@app.route('/doctor/pending_receipts', methods=['GET'])
def pending_receipts():
    doctor_id = request.args.get('doctor_id')
    receipts = Receipt.query.filter_by(doctor_id=doctor_id, status="pending").all()
    return jsonify([receipt.to_dict() for receipt in receipts]), 200

@app.route('/doctor/approve_receipt', methods=['POST'])
def approve_receipt():
    data = request.json
    receipt = Receipt.query.get(data['receipt_id'])
    if not receipt:
        return jsonify({"error": "Receipt not found"}), 404
    receipt.status = data['status']
    db.session.commit()
    return jsonify({"message": "Receipt status updated"}), 200


# Doctor Endpoints
def is_admin():
    user_id = session.get('user_id')
    if not user_id:
        return False
    user = User.query.get(user_id)
    return user and user.role == 'admin'

@app.route('/admin/dashboard', methods=['GET'])
@admin_login_required
def admin_dashboard():
    if not is_admin():
        return redirect(url_for('admin_login'))
    return render_template('admin_dashboard.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        confirm_password = request.form['confirm_password']

        if password != confirm_password:
            flash('Passwords do not match!', 'error')
            return render_template('signup.html')

        # Check if the email is already registered
        if User.query.filter_by(email=email).first():
            flash('Email is already registered!', 'error')
            return render_template('signup.html')

        # Add the user to the database
        new_user = User(email=email, password=password, role="customer")  # Add hashing for passwords
        db.session.add(new_user)
        db.session.commit()

        flash('Signup successful! Please log in.', 'success')
        return redirect(url_for('login'))

    return render_template('signup.html')

@app.route('/customer/create_receipt', methods=['POST'])
def create_receipt():
    
    data = request.json
    new_receipt = Receipt(
        name=data['name'],
        email=data['email'],
        address=data['address'],
        symptoms=data['symptoms'],
        additional_symptoms=data.get('additionalSymptoms', ''),
        daily_life_impact=data['dailyLifeImpact'],
        previous_treatment=data['previousTreatment'],
        symptom_duration=data['symptomDuration'],
        status="pending"
    )
    db.session.add(new_receipt)
    db.session.commit()
    return jsonify({"message": "Receipt created successfully"}), 201

@app.route('/user/receipts', methods=['GET'])
@login_required
def user_receipts():
    user_id = session.get('user_id')
    if not user_id:
        flash("You need to be logged in to view receipts.", "error")
        return redirect(url_for('login'))
    user = User.query.filter(User.id == user_id).first()
    # Fetch the user's receipts
    receipts = Receipt.query.filter_by(email=user.email).all()
    return render_template('user_receipts.html', receipts=receipts)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        # Authenticate user
        user = User.query.filter_by(email=email).first()
        if user and user.password == password:  # Add hashing check in production
            # Set user session
            session['user_id'] = user.id
            session['email'] = user.email
            flash('Login successful!', 'success')

            return redirect(url_for('index'))

        flash('Invalid email or password.', 'error')
        return render_template('login.html')

    return render_template('login.html')

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        # Authenticate user
        user = User.query.filter_by(email=email).first()
        if user and user.password == password and user.role == 'admin':  # Add hashing check in production
            # Set user session
            session['user_id'] = user.id
            session['email'] = user.email
            flash('Login successful!', 'success')

            return redirect(url_for('admin_dashboard'))

        flash('Invalid email or password.', 'error')
        return render_template('admin_login.html')

    return render_template('admin_login.html')
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/faq')
def faq():
    faqs = [
        {"question": "Why TheraCan?", "answer": "TheraCan is an innovative platform..."},
        {"question": "How do I request a repeat prescription?", "answer": "To request a repeat prescription..."},
        {"question": "At which pharmacy can I redeem my prescription?", "answer": "You can redeem your prescription at any pharmacy..."}
    ]
    openIndex = None  # or dynamic based on user interaction
    return render_template('faq.html', faqs=faqs, openIndex=openIndex)

@app.route('/pricing')
def pricing():
    return render_template('pricing.html')


@app.route('/questionnaire')
@login_required
def questionnaire():
    return render_template('questionnaire.html')

@app.route('/about')
def home():
    return render_template('about.html')

diseases_data = {
    "anxiety-and-ptsd": {
        "condition": "anxiety and ptsd",
        "editable_section": {
            "image": "https://canngo.express/wp-content/uploads/2024/07/669be7a0d2c58-1024x642.jpg",
            "top_text": "A science-based approach to treating anxiety disorders and PTSD",
            "bold_text": "Anxiety disorders and PTSD affect millions worldwide and can significantly impact quality of life.",
            "paragraphs": [
                "These persistent psychological stresses can be triggered by various causes, including traumatic experiences, genetic predispositions, or neurological disorders.",
                "Medical cannabis, available by prescription, contains cannabinoids such as THC and CBD, which can help manage stress and anxiety."
            ]
        },
        "benefits": [
            {
                "heading": "Anxiety Relief",
                "description": "CBD has anti-anxiety properties that can help relieve symptoms of anxiety disorders and PTSD."
            },
            {
                "heading": "Improving Sleep Quality",
                "description": "THC and CBD can improve sleep quality, reducing time to fall asleep and increasing sleep duration."
            },
            {
                "heading": "Reduction of Accompanying Symptoms",
                "description": "Medical cannabis can help alleviate other symptoms such as depression and physical ailments."
            }
        ]
    },
   
"chronic-pain": {
    "condition": "chronic pain",
    "editable_section": {
        "image": "https://canngo.express/wp-content/uploads/2024/07/669be7a0d2c58.jpg",
        "top_text": "The Benefits of Prescription Cannabis for Chronic Pain",
        "bold_text": "Chronic pain affects millions of individuals, and prescription cannabis offers a science-based approach to managing it.",
        "paragraphs": [
            "Chronic pain can significantly reduce the quality of life and is often accompanied by symptoms such as inflammation, sleep disorders, and psychological distress.",
            "Medical cannabis contains cannabinoids such as THC and CBD, which can help manage chronic pain and its accompanying symptoms."
        ]
    },
    "benefits": [
        {
            "heading": "Pain Relief",
            "description": "THC, a primary active ingredient in medical cannabis, can modulate pain signals in the brain, reducing the intensity of chronic pain. Studies show that THC has sedative properties, relaxing the mind and reducing pain sensation. Medical cannabis is a viable alternative to opiates and should be considered in consultation with a doctor."
        },
        {
            "heading": "Anti-inflammatory",
            "description": "CBD is known for its anti-inflammatory properties. It reduces inflammatory responses in the body, which often trigger or worsen chronic pain. Additionally, CBD is non-psychoactive and does not cause intoxicating effects."
        },
        {
            "heading": "Reduction of Accompanying Symptoms",
            "description": "Chronic pain is often associated with sleep disorders, anxiety, and depression. Prescription medical cannabis can alleviate these symptoms by acting on the cannabinoid receptors in the brain and body."
        }
    ]
},
"migraine": {
    "condition": "migraines",
    "editable_section": {
        "image": "https://canngo.express/wp-content/uploads/2024/07/669be7a0d2c58.jpg",
        "top_text": "The Benefits of Prescription Cannabis for Migraines",
        "bold_text": "Migraines can significantly affect daily life, but prescription cannabis offers a natural and science-backed solution.",
        "paragraphs": [
            "Migraines are characterized by intense headaches and a range of debilitating symptoms such as nausea, vomiting, and sensitivity to light and sound.",
            "Medical cannabis, with active compounds like THC and CBD, can help manage migraines by targeting the endocannabinoid system, which plays a crucial role in pain and symptom modulation."
        ]
    },
    "benefits": [
        {
            "heading": "Pain Relief",
            "description": "Medical cannabis can effectively relieve the intense headaches that accompany migraine attacks. Cannabinoids like THC and CBD act on the body's endocannabinoid system to modulate pain. Studies show that cannabis can reduce pain intensity and shorten migraine durations."
        },
        {
            "heading": "Reduction of Accompanying Symptoms",
            "description": "Migraines are often accompanied by nausea, vomiting, and sensitivity to light and sound. CBD's antiemetic properties help relieve nausea and vomiting, while both cannabinoids reduce sensitivity to light and sound during an attack."
        },
        {
            "heading": "Prevention",
            "description": "Regular use of medical cannabis can help prevent migraines by stabilizing the endocannabinoid system. This reduces the frequency and severity of attacks, leading to an improved quality of life and less disruption in daily activities."
        }
    ]
},
"sleep-disorders": {
    "condition": "chronic sleep disorders",
    "editable_section": {
        "image": "https://canngo.express/wp-content/uploads/2024/07/669be7a0d2c58.jpg",
        "top_text": "The Benefits of Prescription Cannabis for Chronic Sleep Disorders",
        "bold_text": "Chronic sleep disorders can severely impact quality of life, but prescription cannabis offers a natural and effective remedy.",
        "paragraphs": [
            "Sleep disorders, such as insomnia and difficulty maintaining sleep, are often linked to underlying conditions like anxiety, stress, and chronic pain.",
            "Medical cannabis, containing active compounds like THC and CBD, can help manage these issues by promoting relaxation and improving sleep quality."
        ]
    },
    "benefits": [
        {
            "heading": "Improving Sleep Quality",
            "description": "Medical cannabis can significantly enhance sleep quality. THC (tetrahydrocannabinol) has sedative properties that help reduce the time it takes to fall asleep and increase sleep duration. Studies show that THC prolongs deep sleep phases, leading to a more restful night."
        },
        {
            "heading": "Reduction of Anxiety and Stress",
            "description": "Chronic sleep disorders are often linked to anxiety and stress. CBD (cannabidiol), a key cannabis compound, has calming properties that reduce anxiety and stress by interacting with serotonin receptors in the brain. This leads to improved sleep quality and a holistic approach to addressing stress-induced insomnia."
        },
        {
            "heading": "Treatment of Accompanying Symptoms",
            "description": "Chronic sleep disorders can be accompanied by symptoms such as pain, restlessness, and night waking. Cannabinoids like THC and CBD interact with the endocannabinoid system to regulate pain, inflammation, and mood. This alleviates contributing symptoms, promoting better sleep overall."
        }
    ]
},
"womens-health": {
    "condition": "women's health: PMS and endometriosis",
    "editable_section": {
        "image": "https://canngo.express/wp-content/uploads/2024/07/669be7a0d2c58-1024x642.jpg",
        "top_text": "A Science-Based Approach to Women's Health Using Prescription Cannabis",
        "bold_text": "Women's health includes a multitude of complex complaints that can significantly impact daily life.",
        "paragraphs": [
            "Medical cannabis offers a natural and effective solution to alleviate various women's health problems, including menstrual cramps, endometriosis, premenstrual syndrome (PMS), and menopausal symptoms. These conditions can significantly affect daily life and are often accompanied by severe pain, inflammation, and mood swings.",
            "The body's endocannabinoid system (ECS) plays an essential role in regulating pain, inflammation, and mood. Cannabinoids such as THC (tetrahydrocannabinol) and CBD (cannabidiol), found in medical cannabis, interact directly with ECS receptors. This interaction helps modulate pain signal transmission and reduces inflammatory processes, particularly beneficial for painful menstrual cramps and endometriosis."
        ]
    },
    "benefits": [
        {
            "heading": "Pain Relief",
            "description": "Medical cannabis can significantly relieve pain caused by PMS and endometriosis. THC and CBD interact with the body's endocannabinoid system, modulating pain signals and reducing inflammation."
        },
        {
            "heading": "Reduction of Discomfort",
            "description": "PMS and endometriosis are often accompanied by severe mood swings and emotional distress. CBD's anti-anxiety and mood-stabilizing effects help alleviate irritability and depression."
        },
        {
            "heading": "Improving Sleep Quality",
            "description": "Sleep disorders are common with PMS and endometriosis. THC and CBD improve sleep quality by reducing the time it takes to fall asleep and increasing sleep duration."
        }
    ]
}



    
    
    # Add other disease data here...
}

@app.route('/diseases/<disease_name>')
def disease(disease_name):
    # Retrieve disease data, if available
    disease_data = diseases_data.get(disease_name)
    if disease_data:
        return render_template('disease_page.html', disease_data=disease_data)
    return "Disease not found", 404

if __name__ == "__main__":
    app.run(debug=True)
