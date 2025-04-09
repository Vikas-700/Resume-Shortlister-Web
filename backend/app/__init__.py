from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
import os

# Initialize SQLAlchemy
db = SQLAlchemy()

def create_app():
    app = Flask(__name__)
    
    # Configuration
    basedir = os.path.abspath(os.path.dirname(__file__))
    
    # Database configuration
    db_user = os.environ.get('DB_USER', 'postgres')
    db_password = os.environ.get('DB_PASSWORD', 'root')
    db_host = os.environ.get('DB_HOST', 'localhost')
    db_port = os.environ.get('DB_PORT', '5432')
    db_name = os.environ.get('DB_NAME', 'resume_shortlister')
    
    # Construct PostgreSQL URL - always use PostgreSQL for both local and production
    postgres_url = f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
    app.config['SQLALCHEMY_DATABASE_URI'] = postgres_url
    print(f"Using PostgreSQL database: {postgres_url}")
    
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev')
    app.config['UPLOAD_FOLDER'] = os.path.join(app.root_path, 'static', 'uploads')
    
    # Ensure upload directory exists
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    
    # Initialize extensions
    CORS(app)
    db.init_app(app)  # Initialize db with app
    
    # Import models here to avoid circular imports
    from .models import Job, Candidate
    
    # Create database tables if they don't exist
    with app.app_context():
        try:
            # Only create tables that don't exist yet (don't drop existing tables)
            db.create_all()
            print("Database tables created successfully")
            
            # Test database connection
            db.session.execute('SELECT 1')
            print("Database connection test successful")
        except Exception as e:
            print(f"Error initializing database: {str(e)}")
            raise e
    
    # Register blueprints
    from .routes import main
    app.register_blueprint(main)
    
    return app 