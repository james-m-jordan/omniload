import os
import hashlib
import sqlite3
from flask import Flask, request, jsonify, render_template_string
from boto3.session import Session
from dotenv import load_dotenv
from io import BytesIO

# Load environment variables
load_dotenv()
B2_KEY_ID = os.getenv('B2_KEY_ID')
B2_APPLICATION_KEY = os.getenv('B2_APPLICATION_KEY')
B2_BUCKET = os.getenv('B2_BUCKET')
B2_ENDPOINT = os.getenv('B2_ENDPOINT')

# SQLite setup
DB_PATH = 'metadata.db'
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS files (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        filename TEXT,
        filehash TEXT,
        url TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    conn.commit()
    conn.close()

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
    <style>
        body { font-family: Arial, sans-serif; max-width: 600px; margin: 50px auto; padding: 20px; }
        .upload-form { border: 2px dashed #ccc; padding: 20px; text-align: center; }
        .result { margin-top: 20px; padding: 10px; background: #f0f0f0; }
        .error { color: red; }
        .success { color: green; }
    </style>
</head>
<body>
    <h1>OmniLoad File Uploader</h1>
    <div class="upload-form">
        <form id="uploadForm" enctype="multipart/form-data">
            <input type="file" id="fileInput" required>
            <button type="submit">Upload File</button>
        </form>
    </div>
    <div id="result"></div>
    
    <script>
        document.getElementById('uploadForm').addEventListener('submit', async (e) => {
            e.preventDefault();
            const fileInput = document.getElementById('fileInput');
            const file = fileInput.files[0];
            const formData = new FormData();
            formData.append('file', file);
            
            const resultDiv = document.getElementById('result');
            resultDiv.innerHTML = 'Uploading...';
            
            try {
                const response = await fetch('/upload', {
                    method: 'POST',
                    body: formData
                });
                const data = await response.json();
                
                if (response.ok) {
                    resultDiv.innerHTML = `
                        <div class="result success">
                            <h3>Upload Successful!</h3>
                            <p><strong>Filename:</strong> ${data.filename}</p>
                            <p><strong>Hash:</strong> ${data.hash}</p>
                            <p><strong>URL:</strong> <a href="${data.url}" target="_blank">${data.url}</a></p>
                        </div>
                    `;
                } else {
                    resultDiv.innerHTML = `<div class="result error">Error: ${data.error}</div>`;
                }
            } catch (error) {
                resultDiv.innerHTML = `<div class="result error">Error: ${error.message}</div>`;
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
    
    # Calculate hash
    filehash = hashlib.sha256(file_data).hexdigest()
    
    # Create S3 key with hash prefix
    s3_key = f"{filehash[:8]}_{file.filename}"
    
    try:
        # Upload to B2
        s3.upload_fileobj(
            Fileobj=BytesIO(file_data),
            Bucket=B2_BUCKET,
            Key=s3_key,
            ExtraArgs={'ACL': 'public-read'}  # Make file publicly accessible
        )
        
        # Construct public URL - using the correct B2 format
        # For B2, the public URL format is: https://fNNN.backblazeb2.com/file/BUCKET_NAME/KEY
        # Extract the file number from endpoint (e.g., f004 from s3.us-west-004.backblazeb2.com)
        import re
        if B2_ENDPOINT:
            match = re.search(r's3\.(.+?)\.backblazeb2\.com', B2_ENDPOINT)
            if match:
                region = match.group(1)
                # Convert us-west-004 to f004
                file_num = 'f' + region.split('-')[-1].lstrip('0')
                url = f"https://{file_num}.backblazeb2.com/file/{B2_BUCKET}/{s3_key}"
            else:
                # Fallback to constructed URL
                url = f"{B2_ENDPOINT}/{B2_BUCKET}/{s3_key}"
        else:
            url = f"https://f004.backblazeb2.com/file/{B2_BUCKET}/{s3_key}"
        
        # Store metadata
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('INSERT INTO files (filename, filehash, url) VALUES (?, ?, ?)',
                  (file.filename, filehash, url))
        conn.commit()
        conn.close()
        
        return jsonify({
            'filename': file.filename, 
            'hash': filehash, 
            'url': url
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/files')
def list_files():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT filename, filehash, url, created_at FROM files ORDER BY created_at DESC LIMIT 50')
    files = [{'filename': row[0], 'hash': row[1], 'url': row[2], 'created_at': row[3]} for row in c.fetchall()]
    conn.close()
    return jsonify(files)

if __name__ == '__main__':
    app.run(debug=True) 