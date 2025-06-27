# 🚀 OmniLoad

A fast, secure file upload service with hash-based retrieval. Upload files of ANY size and share them using short, hash-based URLs. A true "omniuploader" that handles everything from tiny text files to massive video files.

## ✨ Features

### Core Features (Latest Update)
- **Unlimited File Sizes**: Upload files up to 10TB (B2's limit) - no artificial restrictions
- **Memory Efficient**: Chunked processing ensures large files won't crash the server
- **Multipart Uploads**: Automatic chunking for files over 100MB for reliable uploads
- **Progress Tracking**: Real-time upload progress with speed and size information
- **Hash-Based URLs**: Every file gets a unique SHA256 hash, accessible via short URLs like `/f/a1b2c3d4`
- **File Upload**: Drag-and-drop or click to upload files to Backblaze B2
- **Search**: Search files by filename or hash
- **Download Tracking**: Track how many times each file has been accessed
- **File Info Pages**: Beautiful pages showing file metadata, download counts, and direct links
- **Smart Disambiguation**: When multiple files share a hash prefix, users see a selection page

### Technical Features
- **SQLite Database**: Lightweight metadata storage with automatic migrations
- **Backblaze B2 Integration**: Reliable cloud storage using S3-compatible API with multipart support
- **Responsive Design**: Works great on desktop and mobile
- **Progress Feedback**: Real-time upload status with percentage and speed
- **Human-Readable Sizes**: File sizes shown in KB, MB, GB, TB format
- **Chunked Hash Calculation**: Memory-efficient SHA256 hashing for large files

## 🛠️ Tech Stack

- **Backend**: Python, Flask
- **Storage**: Backblaze B2 (S3-compatible)
- **Database**: SQLite
- **Deployment**: Railway
- **Frontend**: Vanilla JS, Modern CSS

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- Backblaze B2 account with:
  - A private bucket
  - Application key with read/write permissions

### Local Development

1. **Clone the repository**
   ```bash
   git clone https://github.com/james-m-jordan/omniload.git
   cd omniload
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up environment variables**
   Create a `.env` file:
   ```env
   B2_KEY_ID=your_key_id
   B2_APPLICATION_KEY=your_app_key
   B2_BUCKET=your_bucket_name
   B2_ENDPOINT=https://s3.us-east-005.backblazeb2.com
   ```

4. **Run the app**
   ```bash
   python app.py
   ```

5. **Visit** http://localhost:5000

## 📁 Project Structure

```
omniload/
├── app.py              # Main Flask application
├── requirements.txt    # Python dependencies
├── railway.json        # Railway deployment config
├── metadata.db         # SQLite database (auto-created)
└── README.md          # This file
```

## 🔗 API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Upload page |
| `/upload` | POST | Upload a file |
| `/f/<hash>` | GET | Get file by hash (min 8 chars) |
| `/search` | GET | Search files |
| `/files` | GET | List recent files with metadata (JSON) |
| `/health` | GET | Health check endpoint for monitoring |

**Note**: CORS is enabled for all endpoints, making the API accessible from web applications.

## 🗄️ Database Schema

```sql
CREATE TABLE files (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    filename TEXT NOT NULL,           -- S3 key name
    original_filename TEXT,           -- User's original filename
    filehash TEXT NOT NULL,          -- SHA256 hash
    file_size INTEGER,               -- Size in bytes
    mime_type TEXT,                  -- MIME type
    url TEXT NOT NULL,               -- Public B2 URL
    upload_ip TEXT,                  -- Uploader's IP
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    download_count INTEGER DEFAULT 0  -- Access counter
);
```

## 🚢 Deployment

### Railway (Recommended)

1. **Install Railway CLI**
   ```bash
   npm install -g @railway/cli
   ```

2. **Login and initialize**
   ```bash
   railway login
   railway init
   ```

3. **Set environment variables**
   ```bash
   railway variables set B2_KEY_ID=your_key_id
   railway variables set B2_APPLICATION_KEY=your_app_key
   railway variables set B2_BUCKET=your_bucket_name
   railway variables set B2_ENDPOINT=https://s3.us-east-005.backblazeb2.com
   ```

4. **Deploy**
   ```bash
   railway up
   ```

### Manual Deployment

The app includes a `gunicorn` server for production use:

```bash
gunicorn app:app --bind 0.0.0.0:$PORT
```

## 🔧 Configuration

### Backblaze B2 Setup

1. Create a private bucket
2. Generate an application key with:
   - Read and write access
   - Access to your bucket
3. Note your endpoint (e.g., `s3.us-east-005.backblazeb2.com`)
4. Files are accessible at: `https://f005.backblazeb2.com/file/BUCKET_NAME/FILENAME`

### Environment Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `B2_KEY_ID` | Backblaze Key ID | `0051234567890ab` |
| `B2_APPLICATION_KEY` | Backblaze Application Key | `K005xyz...` |
| `B2_BUCKET` | Bucket name | `my-uploads` |
| `B2_ENDPOINT` | S3 endpoint | `https://s3.us-east-005.backblazeb2.com` |

## 📈 Future Enhancements (Planned Sprints)

### Sprint 3: Enhanced UI & CORS
- File preview for images/videos
- Bulk upload support
- CORS configuration for API usage
- Progress bars for large files

### Sprint 4: Security & Features
- Password-protected files
- Expiring links
- File encryption
- Admin dashboard
- Rate limiting

### Sprint 5: Polish & Scale
- CDN integration
- Virus scanning
- Compression
- Analytics
- API documentation

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📝 License

This project is open source and available under the MIT License.

## 🙏 Acknowledgments

Built with speed and iteration in mind. From idea to production in 90 minutes, then enhanced with proper architecture and features.

---

**Live Demo**: Deploy your own instance to try it out!
**Issues**: Please report any bugs or feature requests in the GitHub issues. 