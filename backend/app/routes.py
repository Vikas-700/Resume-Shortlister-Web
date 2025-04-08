from flask import Blueprint, request, jsonify, current_app, send_from_directory
from werkzeug.utils import secure_filename
import os
from .models import db, Job, Candidate
# Update PyPDF2 import with better error handling
try:
    import PyPDF2
except ImportError:
    print("Error importing PyPDF2, trying alternative installations...")
    try:
        import pypdf as PyPDF2
    except ImportError:
        print("Failed to import any PDF library. PDF processing may fail.")
from docx import Document
from sqlalchemy.exc import SQLAlchemyError
import re
import uuid
import spacy
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
import string

# Initialize Blueprint
main = Blueprint('main', __name__)

# Configure allowed file extensions
ALLOWED_EXTENSIONS = {'pdf', 'docx'}

# Load spaCy model
try:
    nlp = spacy.load("en_core_web_sm")
except Exception as e:
    print(f"Error loading spaCy model: {str(e)}")
    # Set nlp to None if loading fails
    nlp = None

# Initialize NLTK stopwords
try:
    import nltk
    nltk.download('stopwords', quiet=True)
    nltk.download('punkt', quiet=True)
    stop_words = set(stopwords.words('english'))
except Exception as e:
    print(f"Error initializing NLTK: {str(e)}")
    # Fallback to a simple list of common English stopwords
    stop_words = set(['i', 'me', 'my', 'myself', 'we', 'our', 'ours', 'ourselves', 'you', 'your', 'yours',
                   'yourself', 'yourselves', 'he', 'him', 'his', 'himself', 'she', 'her', 'hers',
                   'herself', 'it', 'its', 'itself', 'they', 'them', 'their', 'theirs', 'themselves',
                   'what', 'which', 'who', 'whom', 'this', 'that', 'these', 'those', 'am', 'is', 'are',
                   'was', 'were', 'be', 'been', 'being', 'have', 'has', 'had', 'having', 'do', 'does',
                   'did', 'doing', 'a', 'an', 'the', 'and', 'but', 'if', 'or', 'because', 'as', 'until',
                   'while', 'of', 'at', 'by', 'for', 'with', 'about', 'against', 'between', 'into',
                   'through', 'during', 'before', 'after', 'above', 'below', 'to', 'from', 'up', 'down',
                   'in', 'out', 'on', 'off', 'over', 'under', 'again', 'further', 'then', 'once', 'here',
                   'there', 'when', 'where', 'why', 'how', 'all', 'any', 'both', 'each', 'few', 'more',
                   'most', 'other', 'some', 'such', 'no', 'nor', 'not', 'only', 'own', 'same', 'so',
                   'than', 'too', 'very', 's', 't', 'can', 'will', 'just', 'don', 'should', 'now', 'd',
                   'll', 'm', 'o', 're', 've', 'y', 'ain', 'aren', 'couldn', 'didn', 'doesn', 'hadn',
                   'hasn', 'haven', 'isn', 'ma', 'mightn', 'mustn', 'needn', 'shan', 'shouldn', 'wasn',
                   'weren', 'won', 'wouldn'])

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def extract_text_from_pdf(file_path):
    text = ''
    try:
        with open(file_path, 'rb') as file:
            # First try with PyPDF2 1.26.0 method
            try:
                reader = PyPDF2.PdfFileReader(file)
                # Check if PDF is encrypted
                if reader.isEncrypted:
                    try:
                        reader.decrypt('')  # Try empty password
                    except:
                        pass  # If decrypt fails, we'll still try to read what we can

                for page_num in range(reader.getNumPages()):
                    try:
                        page = reader.getPage(page_num)
                        text += page.extractText() + "\n"
                    except:
                        continue  # Skip problematic pages
            except (AttributeError, TypeError, ImportError):
                # If old method fails, try using newer PyPDF2 version methods
                try:
                    # Reset file position
                    file.seek(0)
                    # For PyPDF2 3.x
                    reader = PyPDF2.PdfReader(file)
                    for page in reader.pages:
                        try:
                            text += page.extract_text() + "\n"
                        except:
                            continue  # Skip problematic pages
                except:
                    pass  # If both methods fail, we'll return empty text
    except Exception as e:
        current_app.logger.error(f"Error reading PDF: {str(e)}")
    
    # If no text was extracted, add placeholder text
    if not text.strip():
        text = "Unable to extract text from PDF. Please check if the document contains selectable text."
    
    return text

def extract_text_from_docx(file_path):
    text = ''
    try:
        doc = Document(file_path)
        for para in doc.paragraphs:
            text += para.text + '\n'
    except Exception as e:
        current_app.logger.error(f"Error reading DOCX: {str(e)}")
    return text

def clean_text(text):
    # Remove URLs and special characters
    text = re.sub(r'http\S+', '', text)
    text = re.sub(r'[^a-zA-Z0-9\s.,;:!?\-&]', '', text)
    
    # Remove punctuation and numbers
    text = text.translate(str.maketrans('', '', string.punctuation))
    text = re.sub(r'\d+', '', text)
    
    # Tokenize and remove stopwords
    words = word_tokenize(text.lower())
    filtered_words = [word for word in words if word not in stop_words and len(word) > 2]
    return ' '.join(filtered_words)

def calculate_score(resume_text, job_description):
    # Clean both texts
    clean_resume = clean_text(resume_text)
    clean_job = clean_text(job_description)
    
    # Create frequency dictionaries
    resume_words = clean_resume.split()
    job_words = clean_job.split()
    
    # Calculate term frequency weights
    job_word_freq = {word: job_words.count(word) for word in set(job_words)}
    resume_word_freq = {word: resume_words.count(word) for word in set(resume_words)}
    
    # Calculate weighted score
    score = 0
    for word, freq in job_word_freq.items():
        if word in resume_word_freq:
            score += (freq * resume_word_freq[word]) * len(word)
    
    # Normalize score
    max_score = sum([(freq**2) * len(word) for word, freq in job_word_freq.items()])
    return round((score / max_score * 100) if max_score > 0 else 0, 2)

def extract_email(text):
    email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    match = re.search(email_pattern, text)
    return match.group(0) if match else ''

def extract_phone(text):
    phone_pattern = r'(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}'
    matches = re.findall(phone_pattern, text)
    if matches:
        phone = re.sub(r'[^\d+]', '', matches[0])
        return phone[:15]
    return ''

def extract_name(text):
    # Skip NLP processing due to compatibility issues
    # Instead use a simple approach to find the name
    
    # Fallback to first line with title case
    lines = text.split('\n')
    for line in lines[:10]:  # Check just the first 10 lines
        line = line.strip()
        if line and len(line.split()) <= 4 and len(line.split()) >= 2:
            words = line.split()
            # Check if first few words look like a name (capitalized, no numbers)
            if all(word[0].isupper() for word in words if word) and not any(char.isdigit() for char in line):
                return line
    
    # Try to extract name from common formats like "Name: John Doe"
    name_patterns = [
        r'name[:\s]+([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,3})',
        r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,3})\s*(?:resume|cv)',
    ]
    
    for pattern in name_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1).strip()
    
    return ''

def extract_address(text):
    # Skip NLP processing due to compatibility issues
    # Instead use regex patterns to find city names
    
    # Common city/location patterns
    city_pattern = r'(?:located|based|live|living|residing|from|in)\s+(?:in|at|near)?\s+([A-Z][a-zA-Z\s]+(?:,\s*[A-Z][a-zA-Z\s]+)*)'
    address_pattern = r'(?:address|location)(?::|is|:is)?\s+([A-Z][a-zA-Z0-9\s,.]+)(?:\.|\n|$)'
    
    # Try to find location using patterns
    for pattern in [city_pattern, address_pattern]:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            # Clean up the match
            location = match.group(1).strip()
            # Remove common non-location words
            for word in ['resume', 'cv', 'curriculum', 'vitae', 'contact', 'details', 'information']:
                location = re.sub(r'\b' + word + r'\b', '', location, flags=re.IGNORECASE)
            return location.strip()
    
    # Try to find any postal code or zip code patterns
    zipcode_patterns = [
        r'[A-Z]{1,2}[0-9][A-Z0-9]? [0-9][A-Z]{2}',  # UK postcodes
        r'\b\d{5}(?:-\d{4})?\b',  # US zipcodes
        r'[A-Z]\d[A-Z] \d[A-Z]\d'  # Canadian postcodes
    ]
    
    for pattern in zipcode_patterns:
        match = re.search(pattern, text)
        if match:
            # Try to find city name near the zipcode
            context = text[max(0, match.start() - 50):min(len(text), match.end() + 50)]
            city_near_zip = re.search(r'([A-Z][a-zA-Z\s]+)(?:,|\s+)(?:\d|\s|[A-Z])+' + re.escape(match.group(0)), context)
            if city_near_zip:
                return city_near_zip.group(1).strip()
            return match.group(0)
    
    return ''

def extract_highest_qualification(text):
    qualifications = {
        'PhD': r'\b(ph\.?d|doctorate)\b',
        'Masters': r'\b(m\.?sc|master\'s|m\.?a|m\.?ed|msc|ma|ms)\b',
        'Bachelors': r'\b(b\.?sc|bachelor\'s|b\.?a|b\.?ed|bsc|ba)\b',
        'Diploma': r'\b(diploma|certificate)\b',
        'High School': r'\b(h\.s|high school|secondary school)\b'
    }
    
    found = []
    text_lower = text.lower()
    for qual, pattern in qualifications.items():
        if re.search(pattern, text_lower):
            found.append(qual)
    
    hierarchy = ['PhD', 'Masters', 'Bachelors', 'Diploma', 'High School']
    for level in hierarchy:
        if level in found:
            return level
    return ''

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
        data = request.get_json()
        if not data or 'title' not in data or 'description' not in data:
            return jsonify({'error': 'Missing required fields'}), 400

        job = Job(title=data['title'], description=data['description'])
        db.session.add(job)
        db.session.commit()
        return jsonify({'id': job.id, 'title': job.title}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@main.route('/api/jobs', methods=['GET'])
def get_jobs():
    try:
        jobs = Job.query.all()
        return jsonify({"jobs": [{'id': j.id, 'title': j.title, 'description': j.description} for j in jobs]})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@main.route('/api/jobs/<int:job_id>', methods=['DELETE'])
def delete_job(job_id):
    try:
        job = Job.query.get_or_404(job_id)
        
        Candidate.query.filter_by(job_id=job_id).delete()
        db.session.delete(job)
        db.session.commit()
        
        return jsonify({
            'message': 'Job deleted successfully',
            'id': job_id
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@main.route('/api/jobs/<int:job_id>/upload-resume', methods=['POST'])
def upload_resume(job_id):
    file_path = None
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['file']
        if not file or file.filename == '':
            return jsonify({'error': 'Invalid file'}), 400
        
        if not allowed_file(file.filename):
            return jsonify({'error': 'Invalid file type'}), 400

        job = Job.query.get_or_404(job_id)
        original_filename = secure_filename(file.filename)
        filename = f"{uuid.uuid4().hex}_{original_filename}"
        file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)

        # Extract text
        if filename.lower().endswith('.pdf'):
            resume_text = extract_text_from_pdf(file_path)
        else:
            resume_text = extract_text_from_docx(file_path)

        if not resume_text.strip():
            raise ValueError("Could not extract text from resume")

        # Process information
        score = calculate_score(resume_text, job.description)
        name = extract_name(resume_text) or request.form.get('name', '')
        email = extract_email(resume_text) or request.form.get('email', '')
        mobile = extract_phone(resume_text) or request.form.get('mobile', '')
        city = extract_address(resume_text) or request.form.get('city', '')
        qualification = extract_highest_qualification(resume_text)

        # Validate required fields - only required if both extracted and form values are empty
        form_email = request.form.get('email', '')
        form_mobile = request.form.get('mobile', '')
        
        # Check if user provided either email or mobile in the form, even if extraction failed
        if not email and not mobile and not form_email and not form_mobile:
            if os.path.exists(file_path):
                os.remove(file_path)
            return jsonify({
                'error': 'Cannot process resume: No email or mobile number found. At least one is required.',
                'extracted_info': {
                    'name': name,
                    'email': email,
                    'mobile': mobile,
                    'city': city,
                    'qualification': qualification
                }
            }), 400
            
        # Use provided values if extraction failed
        if not email and form_email:
            email = form_email
        if not mobile and form_mobile:
            mobile = form_mobile

        # Check for existing candidate
        existing = Candidate.query.filter(
            (Candidate.email == email) | (Candidate.mobile == mobile),
            Candidate.job_id == job_id
        ).first()

        if existing:
            existing.name = name
            existing.mobile = mobile
            existing.city = city
            existing.highest_qualification = qualification
            existing.resume_path = filename
            existing.score = score
            db.session.commit()
            return jsonify({
                'message': 'Candidate updated',
                'candidate_id': existing.candidate_id,
                'score': score,
                'qualification': qualification,
                'extracted_info': {
                    'name': name,
                    'email': email,
                    'mobile': mobile,
                    'city': city,
                    'qualification': qualification
                }
            }), 200

        # Create new candidate
        candidate = Candidate(
            name=name,
            email=email,
            mobile=mobile,
            city=city,
            highest_qualification=qualification,
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
            'qualification': qualification,
            'extracted_info': {
                'name': name,
                'email': email,
                'mobile': mobile,
                'city': city,
                'qualification': qualification
            }
        }), 201

    except Exception as e:
        db.session.rollback()
        if file_path and os.path.exists(file_path):
            try:
                os.remove(file_path)
            except:
                pass
        # Log detailed error information
        import traceback
        error_details = traceback.format_exc()
        current_app.logger.error(f"Resume upload error: {str(e)}\n{error_details}")
        
        # Return a more helpful error message
        return jsonify({
            'error': f"Failed to process resume: {str(e)}",
            'details': "The server encountered an error while processing your resume. Please try again or use a different file format."
        }), 500

@main.route('/api/jobs/<int:job_id>/candidates', methods=['GET'])
def get_candidates(job_id):
    try:
        candidates = Candidate.query.filter_by(job_id=job_id).order_by(Candidate.score.desc()).all()
        return jsonify({"candidates": [{
            'id': c.id,
            'candidate_id': c.candidate_id,
            'name': c.name,
            'email': c.email,
            'mobile': c.mobile,
            'city': c.city,
            'qualification': c.highest_qualification,
            'score': c.score,
            'resume_path': c.resume_path
        } for c in candidates]})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@main.route('/api/top-resumes', methods=['GET'])
def get_top_resumes():
    try:
        limit = request.args.get('limit', default=10, type=int)
        
        query = db.session.query(
            Candidate, 
            Job.title.label('job_title')
        ).join(
            Job, 
            Candidate.job_id == Job.id
        ).order_by(
            Candidate.score.desc()
        ).limit(limit)
        
        results = query.all()
        
        return jsonify({
            'top_resumes': [{
                'id': c.Candidate.id,
                'candidate_id': c.Candidate.candidate_id,
                'name': c.Candidate.name,
                'email': c.Candidate.email,
                'mobile': c.Candidate.mobile,
                'city': c.Candidate.city,
                'qualification': c.Candidate.highest_qualification,
                'score': c.Candidate.score,
                'resume_path': c.Candidate.resume_path,
                'job_id': c.Candidate.job_id,
                'job_title': c.job_title
            } for c in results]
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@main.route('/api/resumes/<filename>', methods=['GET'])
def download_resume(filename):
    try:
        if '..' in filename or filename.startswith('/'):
            return jsonify({'error': 'Invalid filename'}), 400
            
        file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
        
        if not os.path.exists(file_path):
            return jsonify({'error': 'File not found'}), 404
            
        content_type = 'application/pdf' if filename.lower().endswith('.pdf') else 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        
        disposition_type = request.args.get('download', 'false').lower() == 'true'
        
        return send_from_directory(
            current_app.config['UPLOAD_FOLDER'],
            filename,
            mimetype=content_type,
            as_attachment=disposition_type,
            download_name=filename.split('_', 1)[1] if '_' in filename else filename
        )
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Error handler
@main.app_errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Resource not found'}), 404