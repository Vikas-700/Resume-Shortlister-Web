from . import db
from datetime import datetime
import uuid

class Job(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    candidates = db.relationship('Candidate', backref='job', lazy=True)

class Candidate(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    candidate_id = db.Column(db.String(36), default=lambda: str(uuid.uuid4()), unique=True)
    name = db.Column(db.String(100))
    email = db.Column(db.String(100))
    mobile = db.Column(db.String(20))
    city = db.Column(db.String(100), nullable=True)
    resume_path = db.Column(db.String(255))
    score = db.Column(db.Float, default=0.0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    job_id = db.Column(db.Integer, db.ForeignKey('job.id'), nullable=False)
    
    # Add unique constraint to prevent duplicate candidates per job
    __table_args__ = (
        db.UniqueConstraint('email', 'job_id', name='unique_email_per_job'),
        db.UniqueConstraint('resume_path', 'job_id', name='unique_resume_per_job'),
    )