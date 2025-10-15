import os
import logging
from flask import Flask
from dotenv import load_dotenv

# Application version
VERSION = "1.0.0"

# Load environment variables
load_dotenv()

# Check if running in production
def is_production():
    """Check if the application is running in production mode"""
    return os.environ.get('FLASK_ENV', 'development').lower() == 'production'

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)

@app.route('/')
def hello_world():
    """Simple Hello World endpoint"""
    logger.info("Hello World endpoint accessed")
    return '<h1>Hello World</h1><p>Welcome to reports.slide.recipes</p>'

@app.route('/health')
def health_check():
    """Health check endpoint"""
    return {'status': 'healthy', 'version': VERSION}

if __name__ == '__main__':
    # Only run in debug mode if not in production
    debug_mode = not is_production()
    app.run(debug=debug_mode, host='0.0.0.0', port=5000)

