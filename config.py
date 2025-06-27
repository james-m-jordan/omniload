import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration constants
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
ALLOWED_EXTENSIONS = {
    'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif', 'doc', 'docx', 
    'xls', 'xlsx', 'ppt', 'pptx', 'zip', 'csv', 'json', 'xml',
    'mp3', 'mp4', 'avi', 'mov', 'webm'
}

# Dangerous file extensions to block
BLOCKED_EXTENSIONS = {
    'exe', 'bat', 'cmd', 'sh', 'ps1', 'vbs', 'js', 'jar',
    'com', 'scr', 'msi', 'dll', 'app'
}

# Environment variables with validation
B2_KEY_ID = os.getenv('B2_KEY_ID')
B2_APPLICATION_KEY = os.getenv('B2_APPLICATION_KEY')
B2_BUCKET = os.getenv('B2_BUCKET')
B2_ENDPOINT = os.getenv('B2_ENDPOINT')

# Validate required environment variables
required_vars = {
    'B2_KEY_ID': B2_KEY_ID,
    'B2_APPLICATION_KEY': B2_APPLICATION_KEY,
    'B2_BUCKET': B2_BUCKET,
    'B2_ENDPOINT': B2_ENDPOINT
}

missing_vars = [var for var, value in required_vars.items() if not value]
if missing_vars:
    raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")

# Database configuration
DB_PATH = os.getenv('DB_PATH', 'metadata.db')

# Flask configuration
FLASK_SECRET_KEY = os.getenv('FLASK_SECRET_KEY', 'dev-secret-key-change-in-production')
FLASK_ENV = os.getenv('FLASK_ENV', 'production') 