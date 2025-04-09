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

3. PostgreSQL Setup:
   - Install PostgreSQL if not already installed
   - Create a database named `resume_shortlister`:
     ```
     cd backend
     python create_db.py
     ```
   - Or manually create the database:
     ```
     psql -U postgres
     CREATE DATABASE resume_shortlister;
     \q
     ```

4. Set up environment variables (optional):
   - `DB_USER`: PostgreSQL username (default: postgres)
   - `DB_PASSWORD`: PostgreSQL password (default: empty)
   - `DB_HOST`: PostgreSQL host (default: localhost)
   - `DB_PORT`: PostgreSQL port (default: 5432)
   - `DB_NAME`: PostgreSQL database name (default: resume_shortlister)

5. Initialize the database:
   ```
   cd backend
   python -c "from app import db, create_app; app=create_app(); with app.app_context(): db.create_all()"
   ```

6. Run the backend:
   ```
   cd backend
   python run.py
   ```

7. Run the frontend:
   ```
   cd frontend
   npm install
   npm run dev
   ```

## Deployment

### Backend Deployment to Render

1. Push your code to GitHub
2. Create an account on [Render](https://render.com/)
3. Create a new Web Service
   - Connect your GitHub repository
   - Set the build command: `pip install -r backend/requirements.txt && python -c "import nltk; nltk.download('punkt'); nltk.download('stopwords'); nltk.download('wordnet'); nltk.download('averaged_perceptron_tagger')"`
   - Set the start command: `cd backend && gunicorn run:app`
   - Add environment variables:
     - `FLASK_ENV`: production
     - `FLASK_APP`: run.py
     - `SECRET_KEY`: [generate a random secure string]

4. Create a PostgreSQL database on Render and link it to your Web Service

### Frontend Deployment

1. Update the API URL in `frontend/src/App.js` to point to your Render backend
2. Deploy the frontend to GitHub Pages, Vercel, or Netlify

## Tech Stack

- Backend: Flask, SQLAlchemy, NLTK, scikit-learn
- Frontend: React
- Database: PostgreSQL
- Deployment: Render (backend), GitHub Pages (frontend)

## License

MIT 