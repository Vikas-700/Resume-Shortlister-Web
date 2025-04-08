import re
import string
from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords
import PyPDF2
from docx import Document
from flask import current_app
import os
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
                   'than', 'too', 'very', 's', 't', 'can', 'will', 'just', 'don', 'should', 'now', 'd',
                   'll', 'm', 'o', 're', 've', 'y', 'ain', 'aren', 'couldn', 'didn', 'doesn', 'hadn',
                   'hasn', 'haven', 'isn', 'ma', 'mightn', 'mustn', 'needn', 'shan', 'shouldn', 'wasn',
                   'weren', 'won', 'wouldn'])

# Check if scikit-learn is available
try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity
    sklearn_available = True
except ImportError:
    sklearn_available = False

def extract_text_from_pdf(file_path):
    text = ''
    try:
        # Try pdfplumber first (better text extraction)
        try:
            import pdfplumber
            with pdfplumber.open(file_path) as pdf:
                for page in pdf.pages:
                    try:
                        page_text = page.extract_text()
                        if page_text:
                            text += page_text + "\n"
                    except:
                        continue  # Skip problematic pages
        except (ImportError, Exception) as e:
            current_app.logger.warning(f"pdfplumber failed, falling back to PyPDF2: {str(e)}")
            # Fall back to PyPDF2 if pdfplumber fails or isn't installed
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
    text = re.sub(r'http\S+', '', text)
    text = re.sub(r'[^a-zA-Z0-9\s.,;:!?\-&]', '', text)
    text = text.translate(str.maketrans('', '', string.punctuation))
    text = re.sub(r'\d+', '', text)
    words = word_tokenize(text.lower())
    filtered_words = [word for word in words if word not in stop_words and len(word) > 2]
    return ' '.join(filtered_words)

def extract_email(text):
    # More comprehensive pattern to catch various email formats
    email_patterns = [
        r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',  # Standard email
        r'\b[A-Za-z0-9._%+-]+[\s]*@[\s]*[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',  # Email with spaces
        r'\b[A-Za-z0-9._%+-]+[\s]*\(at\)[\s]*[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',  # Email with (at)
        r'\b[A-Za-z0-9._%+-]+[\s]*\[at\][\s]*[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',  # Email with [at]
    ]
    
    for pattern in email_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            # Clean up any spaces or special formats
            email = match.group(0)
            email = email.replace(' ', '').replace('(at)', '@').replace('[at]', '@')
            return email
    
    # Try to find email mentioned in different format like "Email: user at domain.com"
    email_label_pattern = r'(?:e-?mail|id)[\s:]*([A-Za-z0-9._%+-]+[\s]*(?:@|\(at\)|\[at\])[\s]*[A-Za-z0-9.-]+\.[A-Za-z]{2,})'
    match = re.search(email_label_pattern, text, re.IGNORECASE)
    if match:
        email = match.group(1)
        email = email.replace(' ', '').replace('(at)', '@').replace('[at]', '@')
        return email
        
    return ''

def extract_phone(text):
    # Multiple patterns to catch different phone number formats
    phone_patterns = [
        r'(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}',  # Standard formats: (123) 456-7890, 123-456-7890
        r'\+?\d{1,3}[-.\s]?\d{2,3}[-.\s]?\d{2,4}[-.\s]?\d{2,4}',  # International format: +91 98765 43210
        r'\b\d{10}\b',  # Plain 10 digits: 1234567890
        r'\b\d{3}[-.\s]?\d{3}[-.\s]?\d{4}\b',  # Common US format: 123-456-7890
        r'\(\d{3}\)[-.\s]?\d{3}[-.\s]?\d{4}',  # Parentheses format: (123) 456-7890
        r'\b\d{5}[-.\s]?\d{5}\b',  # Format like: 12345 67890
    ]
    
    # Check each pattern
    for pattern in phone_patterns:
        matches = re.findall(pattern, text)
        if matches:
            # Clean the match by removing non-digit characters except + for international prefix
            phone = re.sub(r'[^\d+]', '', matches[0])
            # Limit to a reasonable length to avoid garbage matches
            return phone[:15]
    
    # Try to find phone mentioned after a label like "Phone: 123-456-7890"
    phone_label_pattern = r'(?:phone|mobile|cell|tel|telephone|contact)[\s:]*(\+?\d[-()\s.\d]{7,20})'
    match = re.search(phone_label_pattern, text, re.IGNORECASE)
    if match:
        phone = re.sub(r'[^\d+]', '', match.group(1))
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

def calculate_score(resume_text, job_description):
    if not sklearn_available:
        return 0.0  # Return a default score if scikit-learn is not available
    
    # Clean and preprocess the texts
    resume_text = clean_text(resume_text)
    job_description = clean_text(job_description)
    
    # Create TF-IDF vectors
    vectorizer = TfidfVectorizer(stop_words='english')
    try:
        tfidf_matrix = vectorizer.fit_transform([resume_text, job_description])
        # Calculate cosine similarity
        similarity = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])[0][0]
        return round(similarity * 100, 2)  # Convert to percentage
    except:
        return 0.0  # Return 0 if there's any error in calculation