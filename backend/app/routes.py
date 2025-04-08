from flask import Blueprint, request, jsonify, current_app, send_from_directory
from werkzeug.utils import secure_filename
import os
from .models import db, Job, Candidate
from .extractors import (
    extract_text_from_pdf,
    extract_text_from_docx,
    extract_email,
    extract_phone,
    extract_name,
    extract_address,
    extract_highest_qualification,
    calculate_score
)
from sqlalchemy.exc import SQLAlchemyError
import uuid

# Try to import scikit-learn, but provide fallbacks if not available
try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity
    sklearn_available = True
except ImportError:
    print("scikit-learn not available. Using basic scoring methods only.")
    sklearn_available = False

# Initialize Blueprint
main = Blueprint('main', __name__)

# Configure allowed file extensions
ALLOWED_EXTENSIONS = {'pdf', 'docx'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS



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
            return jsonify({'error': 'Title and description are required'}), 400
        
        # Print the received data for debugging
        print("Received job data:", data)
        
        job = Job(
            title=data['title'],
            description=data['description']
        )
        
        try:
            db.session.add(job)
            db.session.commit()
            return jsonify({
                'message': 'Job created successfully',
                'job': {
                    'id': job.id,
                    'title': job.title,
                    'description': job.description,
                    'created_at': job.created_at.isoformat()
                }
            }), 201
        except Exception as e:
            # Print the database error
            print("Database error:", str(e))
            db.session.rollback()
            return jsonify({'error': f'Database error: {str(e)}'}), 500
            
    except Exception as e:
        # Print any other errors
        print("General error:", str(e))
        return jsonify({'error': f'Failed to create job: {str(e)}'}), 500

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

        # Try to extract text, but don't let extraction failures stop the process
        resume_text = ""
        try:
            if filename.lower().endswith('.pdf'):
                resume_text = extract_text_from_pdf(file_path)
            else:
                resume_text = extract_text_from_docx(file_path)

            # Log the first 100 characters of extracted text for debugging
            current_app.logger.info("Extracted text preview: {}".format(resume_text[:100].replace('\n', ' ') + "..."))
        except Exception as e:
            current_app.logger.error(f"Text extraction error but continuing: {str(e)}")
            resume_text = "Error extracting text from document. Processing with minimal information."

        # Process information - with fallbacks for each extraction
        try:
            score = calculate_score(resume_text, job.description)
        except Exception as e:
            current_app.logger.error(f"Score calculation error but continuing: {str(e)}")
            score = 1.0  # Default minimal score
            
        try:
            name = extract_name(resume_text) or request.form.get('name', '')
        except Exception:
            name = request.form.get('name', '')
            
        try:
            email = extract_email(resume_text) or request.form.get('email', '')
        except Exception:
            email = request.form.get('email', '')
            
        try:
            mobile = extract_phone(resume_text) or request.form.get('mobile', '')
        except Exception:
            mobile = request.form.get('mobile', '')
            
        try:
            city = extract_address(resume_text) or request.form.get('city', '')
        except Exception:
            city = request.form.get('city', '')
            
        try:
            qualification = extract_highest_qualification(resume_text)
        except Exception:
            qualification = ""

        # Log extracted information for debugging
        current_app.logger.info(f"Extracted info - Name: '{name}', Email: '{email}', Mobile: '{mobile}', City: '{city}'")

        # Validate required fields - only required if both extracted and form values are empty
        form_email = request.form.get('email', '')
        form_mobile = request.form.get('mobile', '')
        form_name = request.form.get('name', '')
        
        # Use provided values if extraction failed
        if not email and form_email:
            email = form_email
        if not mobile and form_mobile:
            mobile = form_mobile
        if not name and form_name:
            name = form_name
        
        # Generate a name from the filename if no name was found
        if not name:
            clean_filename = original_filename.replace('.pdf', '').replace('.docx', '')
            name = clean_filename.replace('_', ' ').title()
        
        # Generate placeholder email if needed
        if not email and not mobile:
            import hashlib
            name_hash = hashlib.md5(name.encode()).hexdigest()[:8]
            email = f"candidate_{name_hash}@placeholder.com"
            
        # ALWAYS ACCEPT THE RESUME - we've generated placeholders as needed

        # Check for existing candidate - but don't let this stop us
        try:
            existing = None
            if email:
                existing = Candidate.query.filter(
                    Candidate.email == email,
                    Candidate.job_id == job_id
                ).first()
            
            if not existing and mobile:
                existing = Candidate.query.filter(
                    Candidate.mobile == mobile,
                    Candidate.job_id == job_id
                ).first()
                
            # Log whether we found an existing candidate
            if existing:
                current_app.logger.info(f"Found existing candidate with ID {existing.id}, updating")
                
                # Update the existing candidate
                existing.name = name
                existing.mobile = mobile or existing.mobile
                existing.email = email or existing.email
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
        except Exception as e:
            current_app.logger.error(f"Error checking for existing candidate but continuing: {str(e)}")
            # Continue with creating a new candidate

        # Create new candidate - simplified to reduce failure points
        try:
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
            
            current_app.logger.info(f"Successfully created new candidate with ID {candidate.id}")

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
            current_app.logger.error(f"Error creating candidate: {str(e)}")
            # This is a serious error we can't recover from
            raise

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
        job_id = request.args.get('job_id', default=None, type=int)
        
        query = db.session.query(
            Candidate, 
            Job.title.label('job_title')
        ).join(
            Job, 
            Candidate.job_id == Job.id
        )
        
        # Filter by job_id if provided
        if job_id:
            query = query.filter(Candidate.job_id == job_id)
            
        # Apply limit and ordering
        query = query.order_by(
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