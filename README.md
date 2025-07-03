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

### 🆕 Advanced Features (v3.0)
- **📚 Library System**: Group files together using library hashes (like `library:abc123def456`)
- **🏷️ Tagging System**: Organize files with colored tags (document, image, video, etc.)
- **📝 Rich Metadata**: Add descriptions and custom JSON metadata to files
- **🔗 File Linking**: Create relationships between files (related, depends on, version of, part of)
- **📁 Collections**: Group files into named collections (coming soon)
- **💬 Chat Integration**: Natural language commands in upload interface
- **🎨 Beautiful Dark UI**: Modern, responsive interface with smooth animations
- **📊 Enhanced Gallery**: Card-based file view with inline metadata editing

### Technical Features
- **SQLite Database**: Extended schema with metadata tables and automatic migrations
- **Backblaze B2 Integration**: Reliable cloud storage using S3-compatible API with multipart support
- **Responsive Design**: Works great on desktop and mobile
- **Progress Feedback**: Real-time upload status with percentage and speed
- **Human-Readable Sizes**: File sizes shown in KB, MB, GB, TB format
- **Chunked Hash Calculation**: Memory-efficient SHA256 hashing for large files
- **RESTful API**: Complete API for metadata management and file operations

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

4. **Run database migrations** (for metadata features)
   ```bash
   python db_migrations.py
   ```

5. **Run the app**
   ```bash
   python app.py
   ```

6. **Visit** http://localhost:5000

## 📁 Project Structure

```
omniload/
├── app.py              # Main Flask application
├── db_migrations.py    # Database migration script
├── requirements.txt    # Python dependencies
├── railway.json        # Railway deployment config
├── metadata.db         # SQLite database (auto-created)
├── static/
│   └── styles.css      # Dark theme CSS
├── templates/
│   ├── base.html       # Base template
│   ├── index.html      # Chat-style upload interface
│   ├── files.html      # Gallery view
│   ├── file_info.html  # File details page
│   ├── library.html    # Library view
│   ├── search.html     # Search interface
│   └── ...             # Other templates
└── README.md          # This file
```

## 🔗 API Endpoints

### Core Endpoints
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Upload page with chat interface |
| `/upload` | POST | Upload a file (supports `user_hash` for libraries) |
| `/f/<hash>` | GET | Get file by hash (min 8 chars) |
| `/search` | GET | Search files |
| `/files` | GET | List recent files with metadata (JSON/HTML) |
| `/health` | GET | Health check endpoint for monitoring |
| `/library/<user_hash>` | GET | View all files in a library |

### Metadata API Endpoints
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/files/<id>/metadata` | GET | Get file metadata including tags and links |
| `/api/files/<id>/metadata` | PUT | Update file description and metadata |
| `/api/tags` | GET | List all available tags |
| `/api/tags` | POST | Create a new tag |
| `/api/files/<id>/tags` | POST | Add tag to file |
| `/api/files/<id>/tags` | DELETE | Remove tag from file |
| `/api/files/<id>/links` | POST | Create link between files |
| `/api/files/<id>/links` | DELETE | Remove file link |
| `/api/collections` | GET | List all collections |
| `/api/collections` | POST | Create new collection |

**Note**: CORS is enabled for all endpoints, making the API accessible from web applications.

## 🗄️ Database Schema

### Files Table (Extended)
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
    download_count INTEGER DEFAULT 0, -- Access counter
    description TEXT,                -- File description
    metadata_json TEXT,              -- Custom JSON metadata
    user_hash TEXT                   -- Library grouping hash
);
```

### Metadata Tables
```sql
-- Tags
CREATE TABLE tags (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL,
    color TEXT DEFAULT '#3b82f6',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- File-Tag relationships
CREATE TABLE file_tags (
    file_id INTEGER,
    tag_id INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (file_id, tag_id),
    FOREIGN KEY (file_id) REFERENCES files(id) ON DELETE CASCADE,
    FOREIGN KEY (tag_id) REFERENCES tags(id) ON DELETE CASCADE
);

-- File links
CREATE TABLE file_links (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_file_id INTEGER NOT NULL,
    target_file_id INTEGER NOT NULL,
    link_type TEXT DEFAULT 'related',
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (source_file_id) REFERENCES files(id) ON DELETE CASCADE,
    FOREIGN KEY (target_file_id) REFERENCES files(id) ON DELETE CASCADE
);

-- Collections
CREATE TABLE collections (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    description TEXT,
    icon TEXT DEFAULT '📁',
    color TEXT DEFAULT '#3b82f6',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## 📚 Using Libraries (File Groups)

Libraries allow you to group related files together using a unique hash identifier.

### Creating a Library
1. **Automatic**: Upload any file and a library hash is generated automatically
2. **Manual**: Type `library:your-custom-hash` before uploading

### Adding Files to a Library
```
library:abc123def456
```
Type this command in the chat before uploading files, and they'll be added to that library.

### Viewing Libraries
- Visit `/library/{hash}` to see all files in a library
- Share the URL with others to give them access to the entire collection
- Use `/?library={hash}` to pre-fill the library for uploads

### Example Workflow
```
1. Upload project.pdf → Creates library abc123def456
2. Type "library:abc123def456" + upload source.zip
3. Type "library:abc123def456" + upload demo.mp4
4. Visit /library/abc123def456 to see all 3 files together
5. Share the library URL with your team
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

## 📈 Recent Updates & Future Enhancements

### ✅ Completed Features (v3.0)
- ✅ Beautiful dark UI with chat interface
- ✅ Metadata system (tags, descriptions, custom JSON)
- ✅ File linking and relationships
- ✅ Library system for grouping files
- ✅ Enhanced gallery view with card layout
- ✅ Real-time progress tracking
- ✅ CORS enabled for API usage
- ✅ RESTful metadata API

### 🚀 Planned Enhancements

#### Sprint 4: Media & Preview
- File preview for images/videos in-browser
- Thumbnail generation
- Audio player for music files
- PDF viewer integration
- Code syntax highlighting

#### Sprint 5: Security & Features
- Password-protected files
- Expiring links with time limits
- File encryption at rest
- Admin dashboard
- Rate limiting and abuse prevention
- API key authentication

#### Sprint 6: Scale & Performance
- CDN integration for global delivery
- Virus scanning on upload
- Automatic compression options
- Advanced analytics dashboard
- Full API documentation with examples
- Webhook support for integrations

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