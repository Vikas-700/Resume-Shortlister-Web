from backend.app import create_app, db
from backend.app.models import Job, Candidate

def test_database():
    app = create_app()
    with app.app_context():
        try:
            # Try to create tables
            db.create_all()
            print("Database tables created successfully!")
            
            # Try to create a test job
            test_job = Job(
                title="Test Job",
                description="This is a test job description"
            )
            db.session.add(test_job)
            db.session.commit()
            print("Test job created successfully!")
            
            # Try to query the job
            jobs = Job.query.all()
            print(f"Number of jobs in database: {len(jobs)}")
            
        except Exception as e:
            print(f"Error: {str(e)}")
            db.session.rollback()

if __name__ == "__main__":
    test_database() 