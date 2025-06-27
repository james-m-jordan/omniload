import os
import re
import hashlib
from werkzeug.utils import secure_filename
from config import ALLOWED_EXTENSIONS, BLOCKED_EXTENSIONS, MAX_FILE_SIZE

def allowed_file(filename):
    """Check if file extension is allowed."""
    if '.' not in filename:
        return False
    
    ext = filename.rsplit('.', 1)[1].lower()
    
    # Explicitly block dangerous extensions
    if ext in BLOCKED_EXTENSIONS:
        return False
    
    # If we have a whitelist, use it
    if ALLOWED_EXTENSIONS:
        return ext in ALLOWED_EXTENSIONS
    
    return True

def sanitize_filename(filename):
    """Sanitize filename to prevent directory traversal and other issues."""
    # Get secure version from werkzeug
    filename = secure_filename(filename)
    
    # Additional sanitization
    # Remove any path separators
    filename = filename.replace('/', '').replace('\\', '')
    
    # Limit length
    name, ext = os.path.splitext(filename)
    if len(name) > 100:
        name = name[:100]
    
    # Remove or replace problematic characters
    name = re.sub(r'[^\w\s\-\.]', '_', name)
    
    # Remove multiple spaces/underscores
    name = re.sub(r'[\s_]+', '_', name)
    
    return f"{name}{ext}" if ext else name

def validate_file_size(file_size):
    """Validate file size is within limits."""
    return file_size <= MAX_FILE_SIZE

def calculate_file_hash(file_data):
    """Calculate SHA256 hash of file data."""
    return hashlib.sha256(file_data).hexdigest()

def format_file_size(size_bytes):
    """Format file size in human-readable format."""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} TB"

def construct_b2_url(endpoint, bucket, key):
    """Construct the public B2 URL from endpoint and key."""
    import re
    if endpoint:
        match = re.search(r's3\.(.+?)\.backblazeb2\.com', endpoint)
        if match:
            region = match.group(1)
            # Convert us-east-005 to f005
            file_num = 'f' + region.split('-')[-1]
            return f"https://{file_num}.backblazeb2.com/file/{bucket}/{key}"
    
    # Fallback
    return f"https://f005.backblazeb2.com/file/{bucket}/{key}" 