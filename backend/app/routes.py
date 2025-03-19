from flask import Blueprint, request, jsonify, current_app
from werkzeug.utils import secure_filename
import os
from .models import db, Job, Candidate
import PyPDF2
from docx import Document
from sqlalchemy.exc import SQLAlchemyError
import logging
import re
import uuid

main = Blueprint('main', __name__)

ALLOWED_EXTENSIONS = {'pdf', 'docx'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def extract_text_from_pdf(file_path):
    with open(file_path, 'rb') as file:
        reader = PyPDF2.PdfReader(file)
        text = ''
        for page in reader.pages:
            text += page.extract_text()
    return text

def extract_text_from_docx(file_path):
    doc = Document(file_path)
    text = ''
    for paragraph in doc.paragraphs:
        text += paragraph.text + '\n'
    return text

def extract_email(text):
    # Common email pattern
    email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
    emails = re.findall(email_pattern, text)
    return emails[0] if emails else ''

def extract_phone(text):
    # Common phone number patterns
    phone_patterns = [
        r'\+?[\d\s-]{10,}',  # International format
        r'\(\d{3}\)\s*\d{3}[-.]?\d{4}',  # (123) 456-7890
        r'\d{3}[-.]?\d{3}[-.]?\d{4}',  # 123-456-7890
        r'\d{10}'  # 1234567890
    ]
    
    for pattern in phone_patterns:
        phones = re.findall(pattern, text)
        if phones:
            # Clean up the phone number
            phone = re.sub(r'[^\d+]', '', phones[0])
            if len(phone) >= 10:
                return phone
    return ''

def extract_name(text):
    # Look for common name patterns at the beginning of the document
    # This is a simple approach and might need refinement
    lines = text.split('\n')
    for line in lines[:5]:  # Check first 5 lines
        # Look for lines that are 2-4 words long and don't contain common email/phone patterns
        words = line.strip().split()
        if 2 <= len(words) <= 4 and not re.search(r'@|[\d+]', line):
            return ' '.join(words)
    return ''

def extract_address(text):
    # Look for city names in the text
    # Common city pattern - looking for words that might be cities
    city_patterns = [
        r'(?:City|Location|Address|Located in|Based in|Living in)[\s:]+([A-Z][a-z]+(?:\s[A-Z][a-z]+)?)',  # City: New York
        r'(?:residing|reside|live|based|located)\s+in\s+([A-Z][a-z]+(?:\s[A-Z][a-z]+)?)',  # residing in Chicago
        r'([A-Z][a-z]+(?:\s[A-Z][a-z]+)?),\s+(?:[A-Z]{2}|[A-Za-z]+)\s+\d{5}',  # Chicago, IL 60601
        r'([A-Z][a-z]+(?:\s[A-Z][a-z]+)?)\s+\d{5}',  # Chicago 60601
    ]
    
    for pattern in city_patterns:
        matches = re.findall(pattern, text)
        if matches:
            return matches[0].strip()
    
    # If no city found with specific patterns, try to find capitalized words that might be cities
    # This is a fallback and less accurate
    address_lines = re.findall(r'(?:^|\n)([^,\n]*,[^,\n]*,[^,\n]*)', text)
    for line in address_lines:
        parts = line.split(',')
        if len(parts) >= 2:
            # The city is often the second part in a comma-separated address
            city_part = parts[1].strip()
            # Extract just the city name (first word or two that are capitalized)
            city_match = re.search(r'([A-Z][a-z]+(?:\s[A-Z][a-z]+)?)', city_part)
            if city_match:
                return city_match.group(1)
    
    return ''

def calculate_score(resume_text, job_description):
    # Simple scoring based on keyword matching
    keywords = set(job_description.lower().split())
    resume_words = set(resume_text.lower().split())
    matches = len(keywords.intersection(resume_words))
    return (matches / len(keywords)) * 100 if keywords else 0

def handle_database_error(e):
    current_app.logger.error(f"Database error: {str(e)}")

@main.route('/')
def index():
    return jsonify({
        'message': 'Resume Shortlister API',
        'status': 'running',
        'endpoints': {
            'jobs': '/api/jobs',
            'upload_resume': '/api/jobs/<job_id>/upload-resume',
            'candidates': '/api/jobs/<job_id>/candidates'
        }
    })

@main.route('/api/jobs', methods=['POST'])
def create_job():
    try:
        data = request.json
        current_app.logger.info(f"Received job creation request with data: {data}")
        
        if not data:
            current_app.logger.error("No data received in request")
            return jsonify({'error': 'No data provided'}), 400
            
        if 'title' not in data:
            current_app.logger.error("Missing title in request data")
            return jsonify({'error': 'Missing title'}), 400
            
        if 'description' not in data:
            current_app.logger.error("Missing description in request data")
            return jsonify({'error': 'Missing description'}), 400
        
        job = Job(title=data['title'], description=data['description'])
        current_app.logger.info(f"Creating job: {job.title}")
        
        db.session.add(job)
        db.session.commit()
        
        current_app.logger.info(f"Job created successfully with ID: {job.id}")
        return jsonify({
            'id': job.id,
            'title': job.title,
            'message': 'Job created successfully'
        })
    except Exception as e:
        current_app.logger.error(f"Error creating job: {str(e)}")
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@main.route('/api/jobs', methods=['GET'])
def get_jobs():
    try:
        jobs = Job.query.all()
        return jsonify({
            'jobs': [{
                'id': job.id,
                'title': job.title,
                'description': job.description
            } for job in jobs]
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@main.route('/api/jobs/<int:job_id>/upload-resume', methods=['POST'])
def upload_resume(job_id):
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        if not allowed_file(file.filename):
            return jsonify({'error': f'Invalid file type. Only {", ".join(ALLOWED_EXTENSIONS)} files are allowed'}), 400
        
        job = Job.query.get_or_404(job_id)
        
        # Generate a unique filename to prevent overwriting
        original_filename = secure_filename(file.filename)
        filename = f"{uuid.uuid4().hex}_{original_filename}"
        file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)
        
        # Extract text from resume
        resume_text = ''
        try:
            if filename.lower().endswith('.pdf'):
                resume_text = extract_text_from_pdf(file_path)
            else:  # docx
                resume_text = extract_text_from_docx(file_path)
                
            # Calculate score
            score = calculate_score(resume_text, job.description)
            
            # Extract candidate information automatically or from form data
            name = request.form.get('name', '') or extract_name(resume_text)
            email = request.form.get('email', '') or extract_email(resume_text)
            mobile = request.form.get('mobile', '') or extract_phone(resume_text)
            city = request.form.get('city', '') or extract_address(resume_text)
            
            # Check if either email or mobile is present - at least one is required
            if not email and not mobile:
                # Delete the file since we won't be storing this candidate
                if os.path.exists(file_path):
                    os.remove(file_path)
                return jsonify({
                    'error': 'Cannot process resume: No email or mobile number found. At least one is required.',
                    'extracted_info': {
                        'name': name,
                        'email': email,
                        'mobile': mobile,
                        'city': city
                    }
                }), 400
            
            # Check if candidate already exists for this job (by email)
            existing_candidate = None
            if email:
                existing_candidate = Candidate.query.filter_by(email=email, job_id=job_id).first()
            
            # If candidate exists, update their information instead of creating a new entry
            if existing_candidate:
                existing_candidate.name = name
                existing_candidate.mobile = mobile
                existing_candidate.city = city
                existing_candidate.resume_path = filename
                existing_candidate.score = score
                db.session.commit()
                
                return jsonify({
                    'message': 'Candidate information updated successfully',
                    'candidate_id': existing_candidate.candidate_id,
                    'score': score,
                    'extracted_info': {
                        'name': name,
                        'email': email,
                        'mobile': mobile,
                        'city': city
                    }
                })
            
            # Create new candidate if no duplicate found
            candidate = Candidate(
                name=name,
                email=email,
                mobile=mobile,
                city=city,
                resume_path=filename,
                score=score,
                job_id=job_id
            )
            
            db.session.add(candidate)
            db.session.commit()
            
            return jsonify({
                'message': 'Resume uploaded successfully',
                'candidate_id': candidate.candidate_id,
                'score': score,
                'extracted_info': {
                    'name': name,
                    'email': email,
                    'mobile': mobile,
                    'city': city
                }
            })
        except Exception as e:
            current_app.logger.error(f"Error processing resume: {str(e)}")
            # If there's an error processing the file, make sure to delete it
            if os.path.exists(file_path):
                try:
                    os.remove(file_path)
                except:
                    pass
            raise e
            
    except SQLAlchemyError as e:
        db.session.rollback()
        current_app.logger.error(f"Database error: {str(e)}")
        # Check if the error is due to a unique constraint violation
        if "unique constraint" in str(e).lower() or "duplicate entry" in str(e).lower():
            return jsonify({'error': 'This candidate has already been submitted for this job'}), 409
        return jsonify({'error': str(e)}), 500
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error uploading resume: {str(e)}")
        return jsonify({'error': str(e)}), 500

@main.route('/api/jobs/<int:job_id>/candidates', methods=['GET'])
def get_candidates(job_id):
    try:
        candidates = Candidate.query.filter_by(job_id=job_id).order_by(Candidate.score.desc()).all()
        return jsonify({
            'candidates': [{
                'id': c.id,
                'candidate_id': c.candidate_id,
                'name': c.name,
                'email': c.email,
                'mobile': c.mobile,
                'city': c.city,
                'score': c.score,
                'resume_path': c.resume_path
            } for c in candidates]
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500 