from app import create_app
from app.models import db

app = create_app()

with app.app_context():
    db.drop_all()  # Drop existing tables
    db.create_all()  # Create tables with new schema
    print("Database initialized with updated schema - city column is now nullable") 