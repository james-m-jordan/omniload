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

### Sprint 2.6: Production Polish
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

### Sprint 3.0: Metadata & Libraries (Latest)
- Complete UI redesign with dark theme
- Added comprehensive metadata system
- Implemented file tagging with colors
- Created library system for file grouping
- Added file linking and relationships
- Built chat interface with natural commands
- Created gallery view with card layout
- Added RESTful API for all metadata operations

**Key Features Added**:
- **Database**: Extended schema with 6 new tables
- **UI**: Beautiful dark theme with smooth animations
- **Libraries**: Group files with `library:hash` commands
- **Tags**: Organize with colored labels
- **Metadata**: Descriptions and custom JSON data
- **Links**: Create relationships between files
- **API**: Complete REST endpoints for automation

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

-- Sprint 3 (Metadata & Libraries)
ALTER TABLE files ADD COLUMN description TEXT;
ALTER TABLE files ADD COLUMN metadata_json TEXT;
ALTER TABLE files ADD COLUMN user_hash TEXT;
CREATE INDEX idx_user_hash ON files(user_hash);

-- New metadata tables
CREATE TABLE tags (id, name, color, created_at);
CREATE TABLE file_tags (file_id, tag_id, created_at);
CREATE TABLE file_links (id, source_file_id, target_file_id, link_type, description);
CREATE TABLE collections (id, name, description, icon, color);
CREATE TABLE file_collections (file_id, collection_id, position);
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

### Library System Implementation

```python
# Generate library hash for new uploads
import secrets
user_hash = request.form.get('user_hash', '') or secrets.token_hex(12)

# Parse library commands from chat
library_match = inputValue.match(/library:([a-zA-Z0-9_-]{12,})/i)
if library_match:
    formData.append('user_hash', library_match[1])

# Library endpoint
@app.route('/library/<user_hash>')
def view_library(user_hash):
    # Query all files with matching user_hash
    # Return gallery view of library files
```

### Metadata API Design

```python
# RESTful endpoints for metadata
@app.route('/api/files/<int:file_id>/metadata', methods=['GET', 'PUT'])
@app.route('/api/tags', methods=['GET', 'POST'])
@app.route('/api/files/<int:file_id>/tags', methods=['POST', 'DELETE'])
@app.route('/api/files/<int:file_id>/links', methods=['POST', 'DELETE'])

# JSON metadata storage
metadata = {
    "custom_field": "value",
    "properties": {...}
}
c.execute('UPDATE files SET metadata_json = ?', (json.dumps(metadata),))
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

4. **Test Library System**
   ```bash
   # Upload with library
   curl -X POST -F "file=@test.txt" -F "user_hash=abc123def456" http://localhost:5000/upload
   
   # View library
   http://localhost:5000/library/abc123def456
   ```

5. **Test Metadata API**
   ```bash
   # Get file metadata
   curl http://localhost:5000/api/files/1/metadata
   
   # Update metadata
   curl -X PUT -H "Content-Type: application/json" \
     -d '{"description":"Test file","metadata":{"key":"value"}}' \
     http://localhost:5000/api/files/1/metadata
   
   # Add tag
   curl -X POST -H "Content-Type: application/json" \
     -d '{"tag_id":1}' \
     http://localhost:5000/api/files/1/tags
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

### ✅ Completed in Sprint 3
- [x] Beautiful dark UI redesign
- [x] Progress bars for large files
- [x] CORS configuration
- [x] Copy-to-clipboard for URLs
- [x] Move templates to separate files
- [x] Metadata system with tags
- [x] Library/grouping system
- [x] RESTful API for automation

### Sprint 4: Media & Preview
- [ ] Image/video preview in-browser
- [ ] Thumbnail generation
- [ ] Audio player integration
- [ ] PDF viewer
- [ ] Code syntax highlighting
- [ ] Bulk upload interface

### Sprint 5: Security
- [ ] Rate limiting (flask-limiter)
- [ ] File type validation
- [ ] Password-protected files
- [ ] Expiring links with TTL
- [ ] Admin authentication
- [ ] API key management

### Sprint 6: Scale & Polish
- [ ] Redis for caching
- [ ] CDN integration
- [ ] Virus scanning (ClamAV)
- [ ] Automatic compression
- [ ] Analytics dashboard
- [ ] API documentation (OpenAPI)
- [ ] Webhook support
- [ ] S3 compatibility layer

### Technical Debt
- [ ] Add comprehensive error handling
- [ ] Implement structured logging
- [ ] Add unit and integration tests
- [ ] Create config.py for settings
- [ ] Add database connection pooling
- [ ] Implement rate limiting
- [ ] Add monitoring/alerting

## 🏷️ Working with Metadata

### Tag System
```python
# Default tags created by migration
tags = ['document', 'image', 'video', 'code', 'archive', 'important', 'personal', 'work']

# Tag colors use Tailwind palette
colors = {
    'document': '#10b981',  # green
    'image': '#8b5cf6',     # purple
    'video': '#ef4444',     # red
    # ...
}
```

### Library Commands
```javascript
// Chat commands supported
"library:abc123def456"      // Add to specific library
"u:abc123def456"           // Alias for library
"library abc123def456"     // Natural language variant

// Pre-fill library via URL
"/?library=abc123def456"   // Sets library for session
```

### Metadata Structure
```json
{
  "custom_field": "value",
  "project": "OmniLoad v3",
  "category": "development",
  "keywords": ["upload", "storage", "b2"],
  "related_urls": ["https://..."]
}
```

## 💡 Development Tips

1. **Fast Iteration**: Deploy first, polish later
2. **User Feedback**: Ship early to get real usage data
3. **Simple First**: Complexity can always be added
4. **Document Everything**: Future you will thank you
5. **Git Workflow**: Feature branches keep main stable
6. **Database Migrations**: Always use `db_migrations.py` for schema changes
7. **API Design**: Keep RESTful conventions for consistency

## 📚 Resources

- [Flask Documentation](https://flask.palletsprojects.com/)
- [Backblaze B2 API](https://www.backblaze.com/b2/docs/)
- [Railway Docs](https://docs.railway.app/)
- [SQLite Tutorial](https://sqlite.org/docs.html)

---

**Remember**: This project went from zero to production in 90 minutes. Speed and iteration beat perfection! 