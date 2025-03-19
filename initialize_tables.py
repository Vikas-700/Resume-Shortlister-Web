from backend.app import create_app
from backend.app.models import db

def init_tables():
    app = create_app()
    with app.app_context():
        # Create all tables
        db.create_all()
        print("Tables created successfully!")

if __name__ == "__main__":
    init_tables() 