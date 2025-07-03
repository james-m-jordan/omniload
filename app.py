import os
import hashlib
import sqlite3
import logging
import re
from flask import Flask, request, jsonify, render_template_string, render_template, Response, url_for
from flask_cors import CORS
from werkzeug.utils import secure_filename
from boto3.session import Session
from dotenv import load_dotenv
from io import BytesIO
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Helper functions
def format_file_size(size_bytes):
    """Format file size in human readable format."""
    if size_bytes is None:
        return "Unknown"
    
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} PB"

def calculate_file_hash_chunked(file_obj, chunk_size=8192):
    """Calculate SHA256 hash of a file using chunked reading to save memory."""
    hasher = hashlib.sha256()
    file_obj.seek(0)
    
    while True:
        chunk = file_obj.read(chunk_size)
        if not chunk:
            break
        hasher.update(chunk)
    
    file_obj.seek(0)  # Reset file pointer
    return hasher.hexdigest()

def upload_large_file_multipart(file_obj, bucket, key, file_size):
    """Upload large files using B2's multipart upload API."""
    try:
        # Initialize multipart upload
        response = s3.create_multipart_upload(
            Bucket=bucket,
            Key=key
        )
        upload_id = response['UploadId']
        logger.info(f"Started multipart upload: {upload_id}")
        
        # Upload parts
        parts = []
        part_number = 1
        bytes_uploaded = 0
        
        file_obj.seek(0)
        
        while bytes_uploaded < file_size:
            # Calculate part size (last part might be smaller)
            remaining = file_size - bytes_uploaded
            part_size = min(CHUNK_SIZE, remaining)
            
            # Read chunk
            chunk_data = file_obj.read(part_size)
            
            logger.info(f"Uploading part {part_number} ({format_file_size(part_size)})")
            
            # Upload part
            response = s3.upload_part(
                Bucket=bucket,
                Key=key,
                PartNumber=part_number,
                UploadId=upload_id,
                Body=chunk_data
            )
            
            parts.append({
                'PartNumber': part_number,
                'ETag': response['ETag']
            })
            
            bytes_uploaded += part_size
            part_number += 1
            
            # Log progress
            progress = (bytes_uploaded / file_size) * 100
            logger.info(f"Upload progress: {progress:.1f}% ({format_file_size(bytes_uploaded)}/{format_file_size(file_size)})")
        
        # Complete multipart upload
        response = s3.complete_multipart_upload(
            Bucket=bucket,
            Key=key,
            UploadId=upload_id,
            MultipartUpload={'Parts': parts}
        )
        
        logger.info(f"Multipart upload completed: {key}")
        return True
        
    except Exception as e:
        logger.error(f"Multipart upload failed: {e}")
        
        # Try to abort the upload
        try:
            s3.abort_multipart_upload(
                Bucket=bucket,
                Key=key,
                UploadId=upload_id
            )
            logger.info(f"Aborted multipart upload: {upload_id}")
        except:
            pass
            
        raise e

# Load environment variables
load_dotenv()
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
    logger.error(f"Missing required environment variables: {', '.join(missing_vars)}")
    logger.error("Please set all required environment variables in .env or system environment")
    exit(1)

logger.info("Environment variables loaded successfully")

# SQLite setup
DB_PATH = 'metadata.db'
def init_db():
    """Initialize the database with all necessary columns."""
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        
        # Create table with all columns we need
        c.execute('''CREATE TABLE IF NOT EXISTS files (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT NOT NULL,
            original_filename TEXT,
            filehash TEXT NOT NULL,
            file_size INTEGER,
            mime_type TEXT,
            url TEXT NOT NULL,
            upload_ip TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            download_count INTEGER DEFAULT 0
        )''')
        
        # Create index for faster hash lookups
        c.execute('CREATE INDEX IF NOT EXISTS idx_filehash ON files(filehash)')
        
        # Check if we need to add columns for existing databases
        c.execute("PRAGMA table_info(files)")
        existing_columns = [column[1] for column in c.fetchall()]
        
        # Add missing columns
        columns_to_add = [
            ('original_filename', 'TEXT'),
            ('file_size', 'INTEGER'),
            ('mime_type', 'TEXT'),
            ('upload_ip', 'TEXT'),
            ('download_count', 'INTEGER DEFAULT 0')
        ]
        
        for col_name, col_type in columns_to_add:
            if col_name not in existing_columns:
                c.execute(f'ALTER TABLE files ADD COLUMN {col_name} {col_type}')
                logger.info(f"Added {col_name} column to existing database")
        
        conn.commit()
        conn.close()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        raise

init_db()

# Boto3 S3 client
session = Session()
s3 = session.client(
    service_name='s3',
    aws_access_key_id=B2_KEY_ID,
    aws_secret_access_key=B2_APPLICATION_KEY,
    endpoint_url=B2_ENDPOINT
)

app = Flask(__name__)

# Enable CORS for API usage
CORS(app, origins=["*"], allow_headers=["Content-Type"])

# Configure upload limits - removed artificial limit, let B2 handle it
# B2 supports files up to 10TB, with parts from 5MB to 5GB
app.config['MAX_CONTENT_LENGTH'] = None  # No limit, we'll stream large files
app.config['UPLOAD_FOLDER'] = '/tmp'  # Temporary storage if needed

# Additional configuration for large file handling
app.config['MAX_CONTENT_PATH'] = None
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0

# Enable request streaming for large files
class StreamConsumingMiddleware:
    def __init__(self, app):
        self.app = app

    def __call__(self, environ, start_response):
        # For uploads, don't buffer the entire request
        if environ.get('REQUEST_METHOD') == 'POST' and '/upload' in environ.get('PATH_INFO', ''):
            environ['wsgi.input_terminated'] = True
        return self.app(environ, start_response)

# Apply streaming middleware
app.wsgi_app = StreamConsumingMiddleware(app.wsgi_app)

# B2 multipart upload configuration
CHUNK_SIZE = 100 * 1024 * 1024  # 100MB chunks for multipart uploads
MIN_MULTIPART_SIZE = 100 * 1024 * 1024  # Use multipart for files > 100MB

# Error handler for file too large - removed since we have no limit
# @app.errorhandler(413)
# def request_entity_too_large(error):
#     return jsonify({'error': 'File too large. Maximum size is 100MB'}), 413

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/health')
def health_check():
    """Health check endpoint for monitoring."""
    try:
        # Check database connection
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('SELECT COUNT(*) FROM files')
        file_count = c.fetchone()[0]
        conn.close()
        
        # Check B2 connection
        s3.list_buckets()
        
        return jsonify({
            'status': 'healthy',
            'timestamp': datetime.utcnow().isoformat(),
            'file_count': file_count,
            'version': '2.5.0'  # Large file support version
        }), 200
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return jsonify({
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': datetime.utcnow().isoformat()
        }), 503

@app.route('/upload', methods=['POST'])
def upload_file():
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file part'}), 400
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No selected file'}), 400
        
        # Sanitize filename for security
        safe_filename = secure_filename(file.filename)
        if not safe_filename:
            safe_filename = 'unnamed_file'
        
        # Check file size before reading
        file.seek(0, 2)  # Seek to end
        file_size = file.tell()
        file.seek(0)  # Reset to beginning
        
        logger.info(f"Upload attempt: {safe_filename} ({format_file_size(file_size)})")
        
        # Validate file size
        if file_size == 0:
            return jsonify({'error': 'File is empty'}), 400
        
        # Get file metadata
        mime_type = file.mimetype
        original_filename = safe_filename
        upload_ip = request.remote_addr or 'unknown'
        
        # Calculate hash using chunked reading (memory efficient)
        logger.info(f"Calculating hash for {safe_filename}")
        filehash = calculate_file_hash_chunked(file)
        
        # Create S3 key with hash prefix and sanitized filename
        s3_key = f"{filehash[:8]}_{safe_filename}"
        
        logger.info(f"Uploading to B2: {s3_key} (size: {format_file_size(file_size)})")
        
        # Choose upload method based on file size
        if file_size > MIN_MULTIPART_SIZE:
            # Use multipart upload for large files
            logger.info(f"Using multipart upload for large file ({format_file_size(file_size)})")
            upload_large_file_multipart(file, B2_BUCKET, s3_key, file_size)
        else:
            # Use regular upload for smaller files
            logger.info(f"Using regular upload for file ({format_file_size(file_size)})")
            file.seek(0)  # Reset to beginning
            s3.upload_fileobj(
                Fileobj=file,
                Bucket=B2_BUCKET,
                Key=s3_key
            )
        
        logger.info(f"B2 upload successful: {s3_key}")
        
        # Construct public URL - using the correct B2 format
        # For B2, the public URL format is: https://fNNN.backblazeb2.com/file/BUCKET_NAME/KEY
        # Extract the file number from endpoint (e.g., f005 from s3.us-east-005.backblazeb2.com)
        if B2_ENDPOINT:
            match = re.search(r's3\.(.+?)\.backblazeb2\.com', B2_ENDPOINT)
            if match:
                region = match.group(1)
                # Convert us-east-005 to f005 (keep the leading zeros!)
                file_num = 'f' + region.split('-')[-1]
                url = f"https://{file_num}.backblazeb2.com/file/{B2_BUCKET}/{s3_key}"
            else:
                # Fallback to constructed URL
                url = f"{B2_ENDPOINT}/{B2_BUCKET}/{s3_key}"
        else:
            url = f"https://f005.backblazeb2.com/file/{B2_BUCKET}/{s3_key}"
        
        # Store metadata
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('''INSERT INTO files 
                    (filename, original_filename, filehash, file_size, mime_type, url, upload_ip) 
                    VALUES (?, ?, ?, ?, ?, ?, ?)''',
                  (s3_key, original_filename, filehash, file_size, mime_type, url, upload_ip))
        conn.commit()
        conn.close()
        
        logger.info(f"File uploaded successfully: {original_filename} ({format_file_size(file_size)}) - Hash: {filehash[:8]}")
        
        return jsonify({
            'filename': original_filename, 
            'hash': filehash,
            'hash_short': filehash[:8],
            'size': format_file_size(file_size),
            'url': url,
            'info_url': f"/f/{filehash[:8]}"
        })
    except Exception as e:
        logger.error(f"Upload failed for {safe_filename if 'safe_filename' in locals() else 'unknown'}: {str(e)}")
        logger.exception("Full traceback:")
        return jsonify({'error': f'Upload failed: {str(e)}'}), 500

@app.route('/files')
def list_files():
    """List recent files with full metadata."""
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('''SELECT filename, original_filename, filehash, file_size, 
                            mime_type, created_at, download_count 
                     FROM files 
                     ORDER BY created_at DESC 
                     LIMIT 50''')
        
        files = []
        for row in c.fetchall():
            files.append({
                'filename': row[0],
                'original_filename': row[1] or row[0],
                'hash': row[2],
                'hash_short': row[2][:8] if row[2] else '',
                'size': format_file_size(row[3]) if row[3] else 'Unknown',
                'mime_type': row[4] or 'application/octet-stream',
                'created_at': row[5],
                'download_count': row[6] or 0,
                'info_url': f"/f/{row[2][:8]}" if row[2] else ''
            })
        
        conn.close()
        
        # Check if this is an API request (Accept: application/json)
        if request.headers.get('Accept') == 'application/json' or request.path.endswith('.json'):
            response = jsonify({
                'files': files,
                'count': len(files),
                'limit': 50
            })
            
            # Add rate limit headers (informational)
            response.headers['X-RateLimit-Limit'] = '1000'
            response.headers['X-RateLimit-Remaining'] = '999'
            response.headers['X-RateLimit-Reset'] = str(int(datetime.utcnow().timestamp()) + 3600)
            
            return response
        else:
            # Return HTML template for browser requests
            return render_template('files.html', files=files)
            
    except Exception as e:
        logger.error(f"Error listing files: {e}")
        if request.headers.get('Accept') == 'application/json':
            return jsonify({'error': 'Failed to list files'}), 500
        else:
            return render_template('files.html', files=[], error='Failed to load files')

@app.route('/f/<hash_prefix>')
def get_file_by_hash(hash_prefix):
    """Retrieve file by hash prefix (minimum 8 characters)."""
    if len(hash_prefix) < 8:
        return jsonify({'error': 'Hash prefix must be at least 8 characters'}), 400
    
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        
        # Find files matching the hash prefix
        c.execute('''SELECT filename, original_filename, filehash, file_size, mime_type, url, created_at 
                    FROM files WHERE filehash LIKE ? ORDER BY created_at DESC''', 
                    (hash_prefix + '%',))
        
        results = c.fetchall()
        
        if not results:
            conn.close()
            return render_template('file_not_found.html', hash_prefix=hash_prefix)
        
        if len(results) == 1:
            # Single match - show file info page
            file_data = results[0]
            
            # Increment download count
            c.execute('UPDATE files SET download_count = download_count + 1 WHERE filehash = ?', 
                     (file_data[2],))
            conn.commit()
            
            # Get updated download count
            c.execute('SELECT download_count FROM files WHERE filehash = ?', (file_data[2],))
            download_count = c.fetchone()[0] or 0
            
            conn.close()
            
            return render_template('file_info.html', 
                filename=file_data[0],
                original_filename=file_data[1],
                filehash=file_data[2],
                file_size=format_file_size(file_data[3]) if file_data[3] else 'Unknown',
                mime_type=file_data[4],
                url=file_data[5],
                created_at=file_data[6],
                download_count=download_count,
                request=request
            )
        else:
            # Multiple matches - show disambiguation page
            conn.close()
            return render_template('disambiguation.html', hash_prefix=hash_prefix, files=results)
            
    except Exception as e:
        logger.error(f"Error retrieving file by hash: {e}")
        return jsonify({'error': 'Failed to retrieve file'}), 500

@app.route('/search')
def search_files():
    """Search for files by filename or hash."""
    query = request.args.get('q', '').strip()
    
    if not query:
        return render_template('search.html', query='', results=[], total=0)
    
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        
        # Search in both filename and hash
        search_pattern = f'%{query}%'
        c.execute('''SELECT filename, original_filename, filehash, file_size, url, created_at, download_count
                    FROM files 
                    WHERE original_filename LIKE ? OR filehash LIKE ? OR filename LIKE ?
                    ORDER BY created_at DESC
                    LIMIT 50''', 
                    (search_pattern, search_pattern, search_pattern))
        
        results = [{
            'filename': row[0],
            'original_filename': row[1] or row[0],
            'hash': row[2],
            'hash_short': row[2][:8] if row[2] else '',
            'file_size': format_file_size(row[3]) if row[3] else 'Unknown',
            'url': row[4],
            'created_at': row[5],
            'download_count': row[6] or 0
        } for row in c.fetchall()]
        
        conn.close()
        
        return render_template('search.html', 
                             query=query, 
                             results=results, 
                             total=len(results))
        
    except Exception as e:
        logger.error(f"Search error: {e}")
        return render_template('search.html', 
                             query=query, 
                             results=[], 
                             total=0,
                             error='Search failed. Please try again.')



if __name__ == '__main__':
    # Never run with debug=True in production!
    # Use gunicorn or another production WSGI server
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000))) 