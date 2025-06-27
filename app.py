import os
import logging
import sqlite3
from datetime import datetime
from flask import Flask, request, jsonify, render_template_string
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from boto3.session import Session
from botocore.exceptions import ClientError
from io import BytesIO

# Import our modules
from config import (
    B2_KEY_ID, B2_APPLICATION_KEY, B2_BUCKET, B2_ENDPOINT,
    DB_PATH, FLASK_SECRET_KEY, FLASK_ENV, MAX_FILE_SIZE
)
from utils import (
    allowed_file, sanitize_filename, validate_file_size,
    calculate_file_hash, format_file_size, construct_b2_url
)

# Configure logging
logging.basicConfig(
    level=logging.INFO if FLASK_ENV == 'production' else logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = FLASK_SECRET_KEY
app.config['MAX_CONTENT_LENGTH'] = MAX_FILE_SIZE

# Initialize rate limiter
limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"]
)

# SQLite setup with better error handling
def init_db():
    """Initialize the database with proper error handling."""
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS files (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT NOT NULL,
            original_filename TEXT NOT NULL,
            filehash TEXT NOT NULL,
            file_size INTEGER NOT NULL,
            mime_type TEXT,
            url TEXT NOT NULL,
            upload_ip TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )''')
        c.execute('CREATE INDEX IF NOT EXISTS idx_filehash ON files(filehash)')
        conn.commit()
        conn.close()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        raise

init_db()

# Boto3 S3 client with error handling
try:
    session = Session()
    s3 = session.client(
        service_name='s3',
        aws_access_key_id=B2_KEY_ID,
        aws_secret_access_key=B2_APPLICATION_KEY,
        endpoint_url=B2_ENDPOINT
    )
    logger.info("S3 client initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize S3 client: {e}")
    raise

# Enhanced HTML template with better UX
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>OmniLoad - Secure File Uploader</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        * { box-sizing: border-box; }
        body { 
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            max-width: 800px; 
            margin: 0 auto; 
            padding: 20px;
            background: #f5f5f5;
        }
        .container {
            background: white;
            padding: 30px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        h1 { 
            color: #333; 
            text-align: center;
            margin-bottom: 30px;
        }
        .upload-form { 
            border: 2px dashed #ccc; 
            padding: 40px; 
            text-align: center;
            border-radius: 8px;
            transition: all 0.3s ease;
            cursor: pointer;
        }
        .upload-form.dragover {
            border-color: #4CAF50;
            background: #f0f8f0;
        }
        .file-input {
            display: none;
        }
        .upload-btn {
            background: #4CAF50;
            color: white;
            border: none;
            padding: 12px 30px;
            font-size: 16px;
            border-radius: 5px;
            cursor: pointer;
            transition: background 0.3s;
        }
        .upload-btn:hover {
            background: #45a049;
        }
        .upload-btn:disabled {
            background: #ccc;
            cursor: not-allowed;
        }
        .result { 
            margin-top: 20px; 
            padding: 20px; 
            border-radius: 8px;
            word-break: break-all;
        }
        .error { 
            background: #fee; 
            color: #c33;
            border: 1px solid #fcc;
        }
        .success { 
            background: #efe; 
            color: #3c3;
            border: 1px solid #cfc;
        }
        .progress {
            width: 100%;
            height: 20px;
            background: #f0f0f0;
            border-radius: 10px;
            margin-top: 20px;
            overflow: hidden;
            display: none;
        }
        .progress-bar {
            height: 100%;
            background: #4CAF50;
            width: 0%;
            transition: width 0.3s;
        }
        .file-info {
            margin: 10px 0;
            color: #666;
            font-size: 14px;
        }
        .url-box {
            background: #f5f5f5;
            padding: 10px;
            border-radius: 5px;
            margin: 10px 0;
            font-family: monospace;
            font-size: 14px;
        }
        .limits {
            text-align: center;
            color: #666;
            font-size: 14px;
            margin-top: 20px;
        }
        @media (max-width: 600px) {
            body { padding: 10px; }
            .container { padding: 20px; }
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🚀 OmniLoad File Uploader</h1>
        <div class="upload-form" id="uploadForm">
            <input type="file" id="fileInput" class="file-input">
            <p>Drag and drop a file here or</p>
            <button class="upload-btn" onclick="document.getElementById('fileInput').click()">
                Choose File
            </button>
            <div class="file-info" id="fileInfo"></div>
        </div>
        <div class="progress" id="progress">
            <div class="progress-bar" id="progressBar"></div>
        </div>
        <div id="result"></div>
        <div class="limits">
            Max file size: {{ max_file_size }} | Allowed types: Most common formats
        </div>
    </div>
    
    <script>
        const uploadForm = document.getElementById('uploadForm');
        const fileInput = document.getElementById('fileInput');
        const fileInfo = document.getElementById('fileInfo');
        const progress = document.getElementById('progress');
        const progressBar = document.getElementById('progressBar');
        const resultDiv = document.getElementById('result');
        
        // Drag and drop
        uploadForm.addEventListener('dragover', (e) => {
            e.preventDefault();
            uploadForm.classList.add('dragover');
        });
        
        uploadForm.addEventListener('dragleave', () => {
            uploadForm.classList.remove('dragover');
        });
        
        uploadForm.addEventListener('drop', (e) => {
            e.preventDefault();
            uploadForm.classList.remove('dragover');
            const files = e.dataTransfer.files;
            if (files.length > 0) {
                fileInput.files = files;
                handleFileSelect();
            }
        });
        
        fileInput.addEventListener('change', handleFileSelect);
        
        function handleFileSelect() {
            const file = fileInput.files[0];
            if (file) {
                fileInfo.textContent = `Selected: ${file.name} (${formatFileSize(file.size)})`;
                uploadFile(file);
            }
        }
        
        function formatFileSize(bytes) {
            const units = ['B', 'KB', 'MB', 'GB'];
            let size = bytes;
            let unitIndex = 0;
            while (size >= 1024 && unitIndex < units.length - 1) {
                size /= 1024;
                unitIndex++;
            }
            return `${size.toFixed(1)} ${units[unitIndex]}`;
        }
        
        async function uploadFile(file) {
            const formData = new FormData();
            formData.append('file', file);
            
            resultDiv.innerHTML = '';
            progress.style.display = 'block';
            progressBar.style.width = '0%';
            
            try {
                const xhr = new XMLHttpRequest();
                
                xhr.upload.addEventListener('progress', (e) => {
                    if (e.lengthComputable) {
                        const percentComplete = (e.loaded / e.total) * 100;
                        progressBar.style.width = percentComplete + '%';
                    }
                });
                
                xhr.addEventListener('load', function() {
                    progress.style.display = 'none';
                    if (xhr.status === 200) {
                        const data = JSON.parse(xhr.responseText);
                        resultDiv.innerHTML = `
                            <div class="result success">
                                <h3>✅ Upload Successful!</h3>
                                <p><strong>Filename:</strong> ${data.filename}</p>
                                <p><strong>Size:</strong> ${data.file_size}</p>
                                <p><strong>Hash:</strong> ${data.hash}</p>
                                <div class="url-box">
                                    <strong>URL:</strong> <a href="${data.url}" target="_blank">${data.url}</a>
                                </div>
                            </div>
                        `;
                    } else {
                        const error = JSON.parse(xhr.responseText);
                        resultDiv.innerHTML = `
                            <div class="result error">
                                <h3>❌ Upload Failed</h3>
                                <p>${error.error || 'Unknown error occurred'}</p>
                            </div>
                        `;
                    }
                });
                
                xhr.addEventListener('error', function() {
                    progress.style.display = 'none';
                    resultDiv.innerHTML = `
                        <div class="result error">
                            <h3>❌ Upload Failed</h3>
                            <p>Network error occurred</p>
                        </div>
                    `;
                });
                
                xhr.open('POST', '/upload');
                xhr.send(formData);
                
            } catch (error) {
                progress.style.display = 'none';
                resultDiv.innerHTML = `
                    <div class="result error">
                        <h3>❌ Upload Failed</h3>
                        <p>${error.message}</p>
                    </div>
                `;
            }
        }
    </script>
</body>
</html>
'''

@app.route('/')
def index():
    """Render the upload page."""
    return render_template_string(
        HTML_TEMPLATE,
        max_file_size=format_file_size(MAX_FILE_SIZE)
    )

@app.route('/upload', methods=['POST'])
@limiter.limit("10 per minute")
def upload_file():
    """Handle file upload with validation and error handling."""
    try:
        # Validate file presence
        if 'file' not in request.files:
            logger.warning("Upload attempt with no file part")
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['file']
        if file.filename == '':
            logger.warning("Upload attempt with empty filename")
            return jsonify({'error': 'No file selected'}), 400
        
        # Validate file type
        if not allowed_file(file.filename):
            logger.warning(f"Upload attempt with disallowed file type: {file.filename}")
            return jsonify({'error': 'File type not allowed'}), 400
        
        # Read and validate file size
        file_data = file.read()
        file_size = len(file_data)
        
        if not validate_file_size(file_size):
            logger.warning(f"Upload attempt with oversized file: {file_size} bytes")
            return jsonify({'error': f'File too large. Maximum size is {format_file_size(MAX_FILE_SIZE)}'}), 400
        
        # Process file
        original_filename = file.filename
        safe_filename = sanitize_filename(original_filename)
        filehash = calculate_file_hash(file_data)
        
        # Create S3 key with hash prefix
        s3_key = f"{filehash[:8]}_{safe_filename}"
        
        # Check if file already exists
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('SELECT url FROM files WHERE filehash = ?', (filehash,))
        existing = c.fetchone()
        
        if existing:
            conn.close()
            logger.info(f"Duplicate file detected: {filehash}")
            return jsonify({
                'filename': safe_filename,
                'original_filename': original_filename,
                'hash': filehash,
                'url': existing[0],
                'file_size': format_file_size(file_size),
                'duplicate': True
            })
        
        # Upload to B2
        try:
            s3.upload_fileobj(
                Fileobj=BytesIO(file_data),
                Bucket=B2_BUCKET,
                Key=s3_key,
                ExtraArgs={
                    'ContentType': file.content_type or 'application/octet-stream',
                    'Metadata': {
                        'original-filename': original_filename,
                        'upload-date': datetime.utcnow().isoformat()
                    }
                }
            )
            logger.info(f"File uploaded to B2: {s3_key}")
        except ClientError as e:
            logger.error(f"B2 upload failed: {e}")
            conn.close()
            return jsonify({'error': 'Failed to upload file to storage'}), 500
        
        # Construct public URL
        url = construct_b2_url(B2_ENDPOINT, B2_BUCKET, s3_key)
        
        # Store metadata
        try:
            c.execute('''INSERT INTO files 
                (filename, original_filename, filehash, file_size, mime_type, url, upload_ip) 
                VALUES (?, ?, ?, ?, ?, ?, ?)''',
                (safe_filename, original_filename, filehash, file_size, 
                 file.content_type, url, request.remote_addr))
            conn.commit()
            conn.close()
            logger.info(f"File metadata stored: {filehash}")
        except Exception as e:
            logger.error(f"Database error: {e}")
            # File is uploaded but metadata failed - still return success
            conn.close()
        
        return jsonify({
            'filename': safe_filename,
            'original_filename': original_filename,
            'hash': filehash,
            'url': url,
            'file_size': format_file_size(file_size),
            'duplicate': False
        })
        
    except Exception as e:
        logger.error(f"Unexpected error during upload: {e}")
        return jsonify({'error': 'An unexpected error occurred'}), 500

@app.route('/files')
@limiter.limit("30 per minute")
def list_files():
    """List recent uploads with pagination."""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 50, type=int)
        per_page = min(per_page, 100)  # Max 100 per page
        
        offset = (page - 1) * per_page
        
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        
        # Get total count
        c.execute('SELECT COUNT(*) FROM files')
        total = c.fetchone()[0]
        
        # Get files
        c.execute('''SELECT filename, original_filename, filehash, file_size, url, created_at 
                    FROM files ORDER BY created_at DESC LIMIT ? OFFSET ?''', 
                    (per_page, offset))
        
        files = [{
            'filename': row[0],
            'original_filename': row[1],
            'hash': row[2],
            'file_size': format_file_size(row[3]),
            'url': row[4],
            'created_at': row[5]
        } for row in c.fetchall()]
        
        conn.close()
        
        return jsonify({
            'files': files,
            'page': page,
            'per_page': per_page,
            'total': total,
            'total_pages': (total + per_page - 1) // per_page
        })
        
    except Exception as e:
        logger.error(f"Error listing files: {e}")
        return jsonify({'error': 'Failed to retrieve files'}), 500

@app.route('/health')
def health_check():
    """Health check endpoint for monitoring."""
    try:
        # Check database
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('SELECT 1')
        conn.close()
        
        # Check S3
        s3.head_bucket(Bucket=B2_BUCKET)
        
        return jsonify({'status': 'healthy', 'timestamp': datetime.utcnow().isoformat()})
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return jsonify({'status': 'unhealthy', 'error': str(e)}), 500

@app.errorhandler(413)
def request_entity_too_large(e):
    """Handle file too large errors."""
    return jsonify({'error': f'File too large. Maximum size is {format_file_size(MAX_FILE_SIZE)}'}), 413

@app.errorhandler(429)
def ratelimit_handler(e):
    """Handle rate limit errors."""
    return jsonify({'error': 'Rate limit exceeded. Please try again later.'}), 429

if __name__ == '__main__':
    app.run(debug=(FLASK_ENV != 'production')) 