# Resume Shortlisting System

An automated system for shortlisting resumes using machine learning techniques.

## Features

- Upload and process resumes (PDF, DOCX)
- Extract key information from resumes
- Score candidates based on job requirements
- User-friendly interface
- Real-time processing

## Tech Stack

- Frontend: React.js
- Backend: Flask (Python)
- Database: MySQL
- File Processing: PyPDF2, python-docx

## Live Demo

Frontend: https://vikas-700.github.io/Resume-Shortlister/
Backend: https://resume-shortlister-backend.onrender.com

## Local Development

1. Clone the repository
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   cd frontend
   npm install
   ```
3. Set up environment variables:
   - Create `.env` file in backend directory
   - Add your database credentials and other configurations

4. Run the application:
   ```bash
   # Terminal 1 - Backend
   cd backend
   python run.py

   # Terminal 2 - Frontend
   cd frontend
   npm start
   ```

## Deployment

This project is deployed using:
- Frontend: GitHub Pages
- Backend: Render.com
- Database: MySQL (hosted on Render.com)

## Contributing

1. Fork the repository
2. Create your feature branch
3. Commit your changes
4. Push to the branch
5. Create a new Pull Request 