# Resume Shortlister Web App

A web application for shortlisting resumes based on job descriptions using NLP techniques.

## Features

- Upload and manage job descriptions
- Upload candidate resumes (PDF and DOCX formats)
- Automatic extraction of candidate information (name, email, phone, etc.)
- Score calculation based on resume-job description matching
- View top candidates for each job

## Installation

1. Clone the repository:
   ```
   git clone https://github.com/Vikas-700/Resume-Shortlister-Web.git
   cd Resume-Shortlister-Web
   ```

2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

3. Set up the database:
   ```
   cd backend
   python -c "from app import db, create_app; app=create_app(); with app.app_context(): db.create_all()"
   ```

4. Run the app:
   ```
   cd backend
   python -m flask run
   ```

5. Open a new terminal and run the frontend:
   ```
   cd frontend
   npm install
   npm run dev
   ```

## Tech Stack

- Backend: Flask, SQLAlchemy, NLTK, scikit-learn
- Frontend: React, Material UI
- Database: SQLite (default), MySQL (optional)

## License

MIT 