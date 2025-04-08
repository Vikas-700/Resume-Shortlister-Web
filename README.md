# Resume Shortlister Web App

A web application for shortlisting resumes based on job descriptions using NLP techniques.

## Features

- Upload and manage job descriptions
- Upload candidate resumes (PDF and DOCX formats)
- Automatic extraction of candidate information (name, email, phone, etc.)
- Score calculation based on resume-job description matching
- View top candidates for each job

## Local Installation

1. Clone the repository:
   ```
   git clone https://github.com/Vikas-700/Resume-Shortlister-Web.git
   cd Resume-Shortlister-Web
   ```

2. Install backend dependencies:
   ```
   cd backend
   pip install -r requirements.txt
   ```

3. Run the Flask backend:
   ```
   python -m flask run
   ```

4. Install frontend dependencies:
   ```
   cd ../frontend
   npm install
   ```

5. Run the React frontend:
   ```
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

4. Render will create a PostgreSQL database for you. The application is configured to use the provided `DATABASE_URL`.

### Frontend Deployment

1. Update the API URL in `frontend/src/App.js` to point to your Render backend
2. Deploy the frontend to GitHub Pages, Vercel, or Netlify

## Tech Stack

- Backend: Flask, SQLAlchemy, NLTK, scikit-learn
- Frontend: React
- Database: SQLite (local development), PostgreSQL (production)

## License

MIT 