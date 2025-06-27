# 🛠️ OmniLoad Development Guide

This guide covers the technical details of OmniLoad's implementation, architecture decisions, and development workflow.

## 📋 Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Sprint History](#sprint-history)
3. [Code Structure](#code-structure)
4. [Key Implementation Details](#key-implementation-details)
5. [Testing Locally](#testing-locally)
6. [Deployment Process](#deployment-process)
7. [Troubleshooting](#troubleshooting)
8. [Future Improvements](#future-improvements)

## 🏗️ Architecture Overview

### Tech Stack Rationale

- **Flask**: Lightweight, perfect for rapid development
- **SQLite**: Zero-config database, ideal for metadata
- **Backblaze B2**: Cost-effective S3-compatible storage
- **Railway**: Simple deployment with automatic HTTPS

### Design Decisions

1. **Hash-Based URLs**: SHA256 provides deduplication and security
2. **Minimum 8-char hash prefix**: Balances URL length with uniqueness
3. **Private bucket + public URLs**: Security with accessibility
4. **No user accounts**: Simplicity first, can add later

## 📅 Sprint History

### Sprint 1: Basic Upload (45 minutes)
- Basic Flask app with upload endpoint
- B2 integration with boto3
- SQLite for metadata
- Simple HTML upload form
- Deployed to Railway

**Key Learning**: B2 bucket must be private, use constructed URLs

### Sprint 2: Hash Retrieval (45 minutes)
- Hash-based file access (`/f/<hash>`)
- Search functionality
- Download tracking
- Enhanced UI with drag-and-drop
- File info pages

**Key Features Added**:
- Database migrations
- Human-readable file sizes
- Disambiguation for hash collisions
- Navigation between features

### Sprint 2.5: Large File Support (Latest)
- Removed artificial 100MB file size limit
- Implemented chunked hash calculation for memory efficiency
- Added B2 multipart upload support for files > 100MB
- Progress tracking with real-time upload status
- No more loading entire files into memory
- Support for files up to 10TB (B2's limit)

**Key Improvements**:
- Memory-efficient chunked processing
- B2 multipart upload API integration
- Real-time progress tracking in UI
- Automatic upload method selection based on file size

### Sprint 2.6: Production Polish (Latest)
- Removed debug mode from production
- Added environment variable validation
- Implemented CORS support for API usage
- Added health check endpoint (/health)
- Enhanced security with filename sanitization
- Improved error handling and logging
- Added rate limit headers (informational)
- Enhanced /files endpoint with full metadata

**Production Features**:
- Health monitoring endpoint
- Secure filename handling
- CORS enabled for API integration
- Professional error responses
- No debug mode in production

## 📁 Code Structure

### Main Application (`app.py`)

```python
# Key components:
1. Logging setup
2. Database initialization with migrations
3. Helper functions (format_file_size)
4. Routes:
   - / (upload page)
   - /upload (file upload)
   - /f/<hash> (file retrieval)
   - /search (search files)
   - /files (JSON API)
5. HTML templates (inline)
```

### Database Schema Evolution

```sql
-- Sprint 1 (Basic)
CREATE TABLE files (
    id, filename, filehash, url, created_at
);

-- Sprint 2 (Enhanced)
ALTER TABLE files ADD COLUMN original_filename TEXT;
ALTER TABLE files ADD COLUMN file_size INTEGER;
ALTER TABLE files ADD COLUMN mime_type TEXT;
ALTER TABLE files ADD COLUMN upload_ip TEXT;
ALTER TABLE files ADD COLUMN download_count INTEGER DEFAULT 0;
CREATE INDEX idx_filehash ON files(filehash);
```

## 🔑 Key Implementation Details

### Large File Handling

```python
# Chunked hash calculation (memory efficient)
def calculate_file_hash_chunked(file_obj, chunk_size=8192):
    hasher = hashlib.sha256()
    while chunk := file_obj.read(chunk_size):
        hasher.update(chunk)
    return hasher.hexdigest()

# B2 multipart upload for files > 100MB
def upload_large_file_multipart(file_obj, bucket, key, file_size):
    # Initialize multipart upload
    # Upload in 100MB chunks
    # Track progress and handle errors
    # Complete or abort upload
```

### Upload Strategy

```python
# Automatic method selection
if file_size > MIN_MULTIPART_SIZE:  # 100MB
    upload_large_file_multipart(file, bucket, key, file_size)
else:
    s3.upload_fileobj(file, bucket, key)
```

### B2 URL Construction

```python
# Extract region from endpoint
match = re.search(r's3\.(.+?)\.backblazeb2\.com', B2_ENDPOINT)
region = match.group(1)  # e.g., "us-east-005"
file_num = 'f' + region.split('-')[-1]  # Keep leading zeros!
url = f"https://{file_num}.backblazeb2.com/file/{B2_BUCKET}/{s3_key}"
```

### Hash Prefix Matching

```python
# Minimum 8 characters for uniqueness
if len(hash_prefix) < 8:
    return error

# SQL LIKE for prefix matching
c.execute('SELECT * FROM files WHERE filehash LIKE ?', (hash_prefix + '%',))
```

### Automatic Database Migration

```python
# Check existing columns
c.execute("PRAGMA table_info(files)")
existing_columns = [column[1] for column in c.fetchall()]

# Add missing columns
for col_name, col_type in columns_to_add:
    if col_name not in existing_columns:
        c.execute(f'ALTER TABLE files ADD COLUMN {col_name} {col_type}')
```

## 🧪 Testing Locally

### Basic Testing Flow

1. **Upload a file**
   ```bash
   # Via UI at http://localhost:5000
   # Or via curl:
   curl -X POST -F "file=@test.txt" http://localhost:5000/upload
   ```

2. **Access by hash**
   ```bash
   # Get the hash from upload response
   # Visit: http://localhost:5000/f/a1b2c3d4
   ```

3. **Search**
   ```bash
   # http://localhost:5000/search?q=test
   ```

### Database Inspection

```bash
sqlite3 metadata.db
.tables
.schema files
SELECT * FROM files;
```

## 🚀 Deployment Process

### Railway Deployment

1. **Initial Setup**
   ```bash
   railway login
   railway init
   railway link  # Select existing project
   ```

2. **Environment Variables**
   ```bash
   railway variables set B2_KEY_ID=xxx
   railway variables set B2_APPLICATION_KEY=xxx
   railway variables set B2_BUCKET=xxx
   railway variables set B2_ENDPOINT=xxx
   ```

3. **Deploy**
   ```bash
   railway up -d
   ```

### GitHub Integration

```bash
# Create feature branch
git checkout -b feature-name

# Make changes
git add -A
git commit -m "Description"

# Push and deploy
git push origin feature-name
railway up -d
```

## 🔧 Troubleshooting

### Common Issues

1. **"No module named flask"**
   ```bash
   pip install -r requirements.txt
   ```

2. **B2 Upload Fails**
   - Check credentials in .env
   - Verify bucket exists
   - Ensure key has write permissions

3. **URLs Return 404**
   - Bucket must be private (not public)
   - Check URL construction logic
   - Verify file exists in B2

4. **Database Errors**
   - Delete metadata.db and restart
   - Check migrations ran successfully
   - Verify column names match queries

### Debug Mode

```python
# Enable debug logging
logging.basicConfig(level=logging.DEBUG)

# Flask debug mode (local only!)
app.run(debug=True)
```

## 🚀 Future Improvements

### Sprint 3: UI & UX
- [ ] Image/video preview
- [ ] Bulk upload
- [ ] Progress bars for large files
- [ ] CORS configuration
- [ ] Copy-to-clipboard for URLs

### Sprint 4: Security
- [ ] Rate limiting (flask-limiter)
- [ ] File type validation
- [ ] Size limits
- [ ] Password protection
- [ ] Expiring links
- [ ] Admin authentication

### Sprint 5: Scale & Polish
- [ ] Redis for caching
- [ ] CDN integration
- [ ] Virus scanning
- [ ] Compression
- [ ] Analytics
- [ ] API documentation
- [ ] Webhook support

### Technical Debt
- [ ] Move templates to separate files
- [ ] Add comprehensive error handling
- [ ] Implement proper logging
- [ ] Add unit tests
- [ ] Create config.py for settings
- [ ] Add database connection pooling

## 💡 Development Tips

1. **Fast Iteration**: Deploy first, polish later
2. **User Feedback**: Ship early to get real usage data
3. **Simple First**: Complexity can always be added
4. **Document Everything**: Future you will thank you
5. **Git Workflow**: Feature branches keep main stable

## 📚 Resources

- [Flask Documentation](https://flask.palletsprojects.com/)
- [Backblaze B2 API](https://www.backblaze.com/b2/docs/)
- [Railway Docs](https://docs.railway.app/)
- [SQLite Tutorial](https://sqlite.org/docs.html)

---

**Remember**: This project went from zero to production in 90 minutes. Speed and iteration beat perfection! 