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

from routes import *

if __name__ == "__main__":
    app.run(debug=True)
