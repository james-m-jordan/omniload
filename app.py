import os
import hashlib
import sqlite3
import logging
from flask import Flask, request, jsonify, render_template_string
from boto3.session import Session
from dotenv import load_dotenv
from io import BytesIO

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

# Load environment variables
load_dotenv()
B2_KEY_ID = os.getenv('B2_KEY_ID')
B2_APPLICATION_KEY = os.getenv('B2_APPLICATION_KEY')
B2_BUCKET = os.getenv('B2_BUCKET')
B2_ENDPOINT = os.getenv('B2_ENDPOINT')

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

# Simple HTML form for file upload
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>OmniLoad - File Uploader</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
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
            margin-bottom: 10px;
        }
        .tagline {
            text-align: center;
            color: #666;
            margin-bottom: 30px;
        }
        .nav {
            text-align: center;
            margin-bottom: 30px;
        }
        .nav a {
            color: #4CAF50;
            text-decoration: none;
            margin: 0 15px;
            font-weight: 500;
        }
        .nav a:hover {
            text-decoration: underline;
        }
        .upload-form { 
            border: 3px dashed #4CAF50; 
            padding: 40px; 
            text-align: center;
            border-radius: 10px;
            background: #f9f9f9;
            transition: all 0.3s ease;
        }
        .upload-form.dragover {
            background: #e8f5e9;
            border-color: #2e7d32;
        }
        .upload-btn {
            background: #4CAF50;
            color: white;
            padding: 12px 30px;
            border: none;
            border-radius: 5px;
            font-size: 16px;
            cursor: pointer;
            margin-top: 20px;
        }
        .upload-btn:hover {
            background: #45a049;
        }
        .result { 
            margin-top: 30px; 
            padding: 20px; 
            border-radius: 8px;
        }
        .error { 
            background: #ffebee;
            color: #c62828;
            border: 1px solid #ef5350;
        }
        .success { 
            background: #e8f5e9;
            color: #2e7d32;
            border: 1px solid #66bb6a;
        }
        .result h3 { margin-top: 0; }
        .result p { margin: 10px 0; }
        .result a { 
            color: #4CAF50; 
            text-decoration: none;
            font-weight: 500;
        }
        .result a:hover { text-decoration: underline; }
        .hash-link {
            background: #f5f5f5;
            padding: 8px 12px;
            border-radius: 4px;
            font-family: monospace;
            display: inline-block;
            margin: 5px 0;
        }
        input[type="file"] {
            display: none;
        }
        .file-label {
            display: inline-block;
            padding: 12px 30px;
            background: #f5f5f5;
            border-radius: 5px;
            cursor: pointer;
            transition: all 0.3s ease;
        }
        .file-label:hover {
            background: #e0e0e0;
        }
        .file-name {
            margin-top: 15px;
            color: #666;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🚀 OmniLoad</h1>
        <p class="tagline">Upload files and share them with hash-based URLs</p>
        
        <div class="nav">
            <a href="/">Upload</a>
            <a href="/search">Search Files</a>
            <a href="/files">Recent Files</a>
        </div>
        
        <div class="upload-form" id="uploadArea">
            <form id="uploadForm" enctype="multipart/form-data">
                <p style="font-size: 48px; margin: 0;">📁</p>
                <p style="color: #666; margin: 20px 0;">Drag and drop a file here or</p>
                <label for="fileInput" class="file-label">Choose File</label>
                <input type="file" id="fileInput" required>
                <div class="file-name" id="fileName"></div>
                <button type="submit" class="upload-btn" style="display: none;">Upload File</button>
            </form>
        </div>
        
        <div id="result"></div>
    </div>
    
    <script>
        const uploadArea = document.getElementById('uploadArea');
        const fileInput = document.getElementById('fileInput');
        const fileName = document.getElementById('fileName');
        const uploadBtn = document.querySelector('.upload-btn');
        const uploadForm = document.getElementById('uploadForm');
        
        // File selection
        fileInput.addEventListener('change', (e) => {
            if (e.target.files.length > 0) {
                fileName.textContent = e.target.files[0].name;
                uploadBtn.style.display = 'inline-block';
            }
        });
        
        // Drag and drop
        uploadArea.addEventListener('dragover', (e) => {
            e.preventDefault();
            uploadArea.classList.add('dragover');
        });
        
        uploadArea.addEventListener('dragleave', () => {
            uploadArea.classList.remove('dragover');
        });
        
        uploadArea.addEventListener('drop', (e) => {
            e.preventDefault();
            uploadArea.classList.remove('dragover');
            
            if (e.dataTransfer.files.length > 0) {
                fileInput.files = e.dataTransfer.files;
                fileName.textContent = e.dataTransfer.files[0].name;
                uploadBtn.style.display = 'inline-block';
            }
        });
        
        // Form submission
        uploadForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const file = fileInput.files[0];
            const formData = new FormData();
            formData.append('file', file);
            
            const resultDiv = document.getElementById('result');
            resultDiv.innerHTML = '<div class="result">⏳ Uploading...</div>';
            
            try {
                const response = await fetch('/upload', {
                    method: 'POST',
                    body: formData
                });
                const data = await response.json();
                
                if (response.ok) {
                    resultDiv.innerHTML = `
                        <div class="result success">
                            <h3>✅ Upload Successful!</h3>
                            <p><strong>File:</strong> ${data.filename}</p>
                            <p><strong>Size:</strong> ${data.size}</p>
                            <p><strong>Hash:</strong> <code>${data.hash}</code></p>
                            <p><strong>Short URL:</strong> 
                                <a href="${data.info_url}" class="hash-link">${window.location.origin}${data.info_url}</a>
                            </p>
                            <p><strong>Direct URL:</strong> 
                                <a href="${data.url}" target="_blank">${data.url}</a>
                            </p>
                        </div>
                    `;
                    // Reset form
                    uploadForm.reset();
                    fileName.textContent = '';
                    uploadBtn.style.display = 'none';
                } else {
                    resultDiv.innerHTML = `<div class="result error">❌ Error: ${data.error}</div>`;
                }
            } catch (error) {
                resultDiv.innerHTML = `<div class="result error">❌ Error: ${error.message}</div>`;
            }
        });
    </script>
</body>
</html>
'''

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    
    # Read file data
    file_data = file.read()
    file.seek(0)  # Reset file pointer
    
    # Get file metadata
    file_size = len(file_data)
    mime_type = file.mimetype
    original_filename = file.filename
    upload_ip = request.remote_addr
    
    # Calculate hash
    filehash = hashlib.sha256(file_data).hexdigest()
    
    # Create S3 key with hash prefix
    s3_key = f"{filehash[:8]}_{file.filename}"
    
    try:
        # Upload to B2
        s3.upload_fileobj(
            Fileobj=BytesIO(file_data),
            Bucket=B2_BUCKET,
            Key=s3_key
            # Note: Removed ACL since bucket is private
        )
        
        # Construct public URL - using the correct B2 format
        # For B2, the public URL format is: https://fNNN.backblazeb2.com/file/BUCKET_NAME/KEY
        # Extract the file number from endpoint (e.g., f005 from s3.us-east-005.backblazeb2.com)
        import re
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
        logger.error(f"Upload failed: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/files')
def list_files():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT filename, filehash, url, created_at FROM files ORDER BY created_at DESC LIMIT 50')
    files = [{'filename': row[0], 'hash': row[1], 'url': row[2], 'created_at': row[3]} for row in c.fetchall()]
    conn.close()
    return jsonify(files)

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
            return render_template_string('''
                <!DOCTYPE html>
                <html>
                <head>
                    <title>File Not Found - OmniLoad</title>
                    <meta name="viewport" content="width=device-width, initial-scale=1.0">
                    <style>
                        body { 
                            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                            max-width: 600px; 
                            margin: 50px auto; 
                            padding: 20px;
                            text-align: center;
                        }
                        .error { color: #c33; }
                        a { color: #4CAF50; text-decoration: none; }
                        a:hover { text-decoration: underline; }
                    </style>
                </head>
                <body>
                    <h1>❌ File Not Found</h1>
                    <p class="error">No file found with hash starting with: <code>{{ hash_prefix }}</code></p>
                    <p><a href="/">← Back to Upload</a></p>
                </body>
                </html>
            ''', hash_prefix=hash_prefix)
        
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
            
            return render_template_string('''
                <!DOCTYPE html>
                <html>
                <head>
                    <title>{{ original_filename }} - OmniLoad</title>
                    <meta name="viewport" content="width=device-width, initial-scale=1.0">
                    <style>
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
                        h1 { color: #333; }
                        .file-info {
                            background: #f9f9f9;
                            padding: 20px;
                            border-radius: 8px;
                            margin: 20px 0;
                        }
                        .file-info p {
                            margin: 10px 0;
                            display: flex;
                            justify-content: space-between;
                        }
                        .file-info strong { color: #666; }
                        .download-btn {
                            display: inline-block;
                            background: #4CAF50;
                            color: white;
                            padding: 12px 30px;
                            text-decoration: none;
                            border-radius: 5px;
                            margin: 20px 0;
                        }
                        .download-btn:hover {
                            background: #45a049;
                        }
                        .hash {
                            font-family: monospace;
                            font-size: 14px;
                            word-break: break-all;
                        }
                        .stats {
                            color: #666;
                            font-size: 14px;
                            margin-top: 20px;
                        }
                        a { color: #4CAF50; text-decoration: none; }
                        a:hover { text-decoration: underline; }
                    </style>
                </head>
                <body>
                    <div class="container">
                        <h1>📄 {{ original_filename or filename }}</h1>
                        
                        <div class="file-info">
                            <p><strong>Filename:</strong> <span>{{ filename }}</span></p>
                            {% if original_filename %}
                            <p><strong>Original Name:</strong> <span>{{ original_filename }}</span></p>
                            {% endif %}
                            <p><strong>Size:</strong> <span>{{ file_size }}</span></p>
                            <p><strong>Type:</strong> <span>{{ mime_type or 'Unknown' }}</span></p>
                            <p><strong>Uploaded:</strong> <span>{{ created_at }}</span></p>
                            <p><strong>Downloads:</strong> <span>{{ download_count }}</span></p>
                            <p><strong>Hash:</strong> <span class="hash">{{ filehash }}</span></p>
                        </div>
                        
                        <div style="text-align: center;">
                            <a href="{{ url }}" class="download-btn" target="_blank">⬇️ Download File</a>
                        </div>
                        
                        <div class="stats">
                            <p>Short URL: <code>{{ request.host_url }}f/{{ filehash[:8] }}</code></p>
                            <p>Direct URL: <a href="{{ url }}" target="_blank">{{ url }}</a></p>
                        </div>
                        
                        <p style="text-align: center; margin-top: 30px;">
                            <a href="/">← Upload Another File</a> | 
                            <a href="/search">Search Files</a>
                        </p>
                    </div>
                </body>
                </html>
            ''', 
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
            return render_template_string('''
                <!DOCTYPE html>
                <html>
                <head>
                    <title>Multiple Files Found - OmniLoad</title>
                    <meta name="viewport" content="width=device-width, initial-scale=1.0">
                    <style>
                        body { 
                            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                            max-width: 800px; 
                            margin: 0 auto; 
                            padding: 20px;
                        }
                        h1 { color: #333; }
                        .file-list {
                            list-style: none;
                            padding: 0;
                        }
                        .file-list li {
                            background: #f5f5f5;
                            padding: 15px;
                            margin: 10px 0;
                            border-radius: 5px;
                        }
                        .file-list a {
                            color: #4CAF50;
                            text-decoration: none;
                            font-weight: bold;
                        }
                        .file-list a:hover {
                            text-decoration: underline;
                        }
                        .hash { 
                            font-family: monospace; 
                            font-size: 12px;
                            color: #666;
                        }
                    </style>
                </head>
                <body>
                    <h1>🔍 Multiple Files Found</h1>
                    <p>Multiple files match the hash prefix <code>{{ hash_prefix }}</code>. Please select one:</p>
                    
                    <ul class="file-list">
                        {% for file in files %}
                        <li>
                            <a href="/f/{{ file[2][:16] }}">{{ file[1] or file[0] }}</a><br>
                            <span class="hash">{{ file[2] }}</span><br>
                            <small>Uploaded: {{ file[6] }}</small>
                        </li>
                        {% endfor %}
                    </ul>
                    
                    <p><a href="/">← Back to Upload</a></p>
                </body>
                </html>
            ''', hash_prefix=hash_prefix, files=results)
            
    except Exception as e:
        logger.error(f"Error retrieving file by hash: {e}")
        return jsonify({'error': 'Failed to retrieve file'}), 500

@app.route('/search')
def search_files():
    """Search for files by filename or hash."""
    query = request.args.get('q', '').strip()
    
    if not query:
        return render_template_string(SEARCH_TEMPLATE, query='', results=[], total=0)
    
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
        
        return render_template_string(SEARCH_TEMPLATE, 
                                    query=query, 
                                    results=results, 
                                    total=len(results))
        
    except Exception as e:
        logger.error(f"Search error: {e}")
        return render_template_string(SEARCH_TEMPLATE, 
                                    query=query, 
                                    results=[], 
                                    total=0,
                                    error='Search failed. Please try again.')

# Search template
SEARCH_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>Search Files - OmniLoad</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
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
        h1 { color: #333; text-align: center; }
        .search-box {
            display: flex;
            margin: 20px 0;
        }
        .search-box input {
            flex: 1;
            padding: 12px;
            font-size: 16px;
            border: 2px solid #ddd;
            border-radius: 5px 0 0 5px;
        }
        .search-box button {
            padding: 12px 30px;
            background: #4CAF50;
            color: white;
            border: none;
            border-radius: 0 5px 5px 0;
            cursor: pointer;
            font-size: 16px;
        }
        .search-box button:hover {
            background: #45a049;
        }
        .results {
            margin-top: 30px;
        }
        .result-item {
            background: #f9f9f9;
            padding: 15px;
            margin: 10px 0;
            border-radius: 8px;
            border-left: 4px solid #4CAF50;
        }
        .result-item h3 {
            margin: 0 0 10px 0;
        }
        .result-item a {
            color: #4CAF50;
            text-decoration: none;
        }
        .result-item a:hover {
            text-decoration: underline;
        }
        .meta {
            font-size: 14px;
            color: #666;
        }
        .hash {
            font-family: monospace;
            font-size: 12px;
        }
        .error {
            color: #c33;
            text-align: center;
            margin: 20px 0;
        }
        .nav {
            text-align: center;
            margin-top: 30px;
        }
        .nav a {
            color: #4CAF50;
            text-decoration: none;
            margin: 0 10px;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🔍 Search Files</h1>
        
        <form method="get" action="/search">
            <div class="search-box">
                <input type="text" name="q" value="{{ query }}" placeholder="Search by filename or hash..." autofocus>
                <button type="submit">Search</button>
            </div>
        </form>
        
        {% if error %}
        <p class="error">{{ error }}</p>
        {% endif %}
        
        {% if query %}
        <div class="results">
            <p>Found {{ total }} result(s) for "{{ query }}"</p>
            
            {% if results %}
                {% for file in results %}
                <div class="result-item">
                    <h3><a href="/f/{{ file.hash_short }}">{{ file.original_filename }}</a></h3>
                    <div class="meta">
                        Size: {{ file.file_size }} | 
                        Uploaded: {{ file.created_at }} | 
                        Downloads: {{ file.download_count }}
                    </div>
                    <div class="hash">Hash: {{ file.hash }}</div>
                </div>
                {% endfor %}
            {% else %}
                <p style="text-align: center; color: #666;">No files found matching your search.</p>
            {% endif %}
        </div>
        {% endif %}
        
        <div class="nav">
            <a href="/">← Upload Files</a> |
            <a href="/files">Browse All Files</a>
        </div>
    </div>
</body>
</html>
'''

if __name__ == '__main__':
    app.run(debug=True) 