import os
from app import create_app

# Set development environment if not already set
if not os.environ.get('FLASK_ENV'):
    os.environ['FLASK_ENV'] = 'development'

# Create the app
app = create_app()

if __name__ == '__main__':
    app.run(debug=True, port=5000) 