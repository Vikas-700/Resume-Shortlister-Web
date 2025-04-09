import re
import string
from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords
import PyPDF2
from docx import Document
from flask import current_app
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

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
                   'than', 'too', 'very', 's', 't', 'can', 'will', 'just', 'don', 'should', 'now'])

# Check if scikit-learn is available
try:
    sklearn_available = True
except NameError:
    sklearn_available = False

def extract_text_from_pdf(file_path):
    text = ''
    try:
        # Try pdfplumber first (better text extraction)
        try:
            import pdfplumber
            with pdfplumber.open(file_path) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
        except ImportError:
            # Fall back to PyPDF2
            with open(file_path, 'rb') as file:
                try:
                    # For PyPDF2 3.x
                    reader = PyPDF2.PdfReader(file)
                    for page in reader.pages:
                        text += page.extract_text() + "\n"
                except Exception:
                    # Try old PyPDF2 version
                    file.seek(0)
                    reader = PyPDF2.PdfFileReader(file)
                    for page_num in range(reader.getNumPages()):
                        text += reader.getPage(page_num).extractText() + "\n"
    except Exception as e:
        current_app.logger.error(f"Error reading PDF: {str(e)}")
    
    return text.strip() or "Unable to extract text from PDF."

def extract_text_from_docx(file_path):
    text = ''
    try:
        doc = Document(file_path)
        for para in doc.paragraphs:
            text += para.text + '\n'
    except Exception as e:
        current_app.logger.error(f"Error reading DOCX: {str(e)}")
    return text.strip() or "Unable to extract text from DOCX."

def clean_text(text):
    text = re.sub(r'http\S+', '', text)
    text = re.sub(r'[^a-zA-Z0-9\s.,;:!?\-&]', '', text)
    text = text.translate(str.maketrans('', '', string.punctuation))
    text = re.sub(r'\d+', '', text)
    words = word_tokenize(text.lower())
    filtered_words = [word for word in words if word not in stop_words and len(word) > 2]
    return ' '.join(filtered_words)

def extract_email(text):
    # Standard email pattern
    email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    match = re.search(email_pattern, text, re.IGNORECASE)
    if match:
        return match.group(0)
    return ''

def extract_phone(text):
    # Common phone patterns
    phone_patterns = [
        r'(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}',  # (123) 456-7890, 123-456-7890
        r'\b\d{10}\b',  # 1234567890
    ]
    
    for pattern in phone_patterns:
        match = re.search(pattern, text)
        if match:
            # Clean the match
            phone = re.sub(r'[^\d+]', '', match.group(0))
            return phone[:15]  # Limit length
    return ''

def extract_name(text):
    # Look for name in the first few lines
    lines = text.split('\n')
    for line in lines[:10]:
        line = line.strip()
        if line and 2 <= len(line.split()) <= 4:
            words = line.split()
            if all(word[0].isupper() for word in words if word) and not any(char.isdigit() for char in line):
                return line
    return ''

def extract_address(text):
    # Simple city pattern
    city_pattern = r'(?:located|based|live|living|residing|from|in)\s+(?:in|at|near)?\s+([A-Z][a-zA-Z\s]+)'
    match = re.search(city_pattern, text, re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return ''

def extract_highest_qualification(text):
    qualifications = {
        'PhD': r'\b(ph\.?d|doctorate)\b',
        'Masters': r'\b(m\.?sc|master\'s|m\.?a|m\.?ed|msc|ma|ms)\b',
        'Bachelors': r'\b(b\.?sc|bachelor\'s|b\.?a|b\.?ed|bsc|ba)\b',
        'Diploma': r'\b(diploma|certificate)\b',
        'High School': r'\b(h\.s|high school|secondary school)\b'
    }
    
    # Check each qualification level
    for level, pattern in qualifications.items():
        if re.search(pattern, text, re.IGNORECASE):
            return level
    
    return ''

def calculate_score(resume_text, job_description):
    if not resume_text or not job_description:
        return 0.0
    
    try:
        if sklearn_available:
            # Use TF-IDF vectorization and cosine similarity for better matching
            vectorizer = TfidfVectorizer()
            texts = [clean_text(resume_text), clean_text(job_description)]
            tfidf_matrix = vectorizer.fit_transform(texts)
            similarity = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])[0][0]
            # Convert to percentage
            return round(similarity * 100, 2)
        else:
            # Fallback to simple word overlap
            resume_words = set(clean_text(resume_text).split())
            job_words = set(clean_text(job_description).split())
            
            if not resume_words or not job_words:
                return 0.0
                
            # Calculate overlap
            common_words = resume_words.intersection(job_words)
            score = (len(common_words) / len(job_words)) * 100
            return round(score, 2)
    except Exception as e:
        current_app.logger.error(f"Score calculation error: {str(e)}")
        return 0.0