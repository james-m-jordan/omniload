# OmniLoad - Cloud File Uploader with Hash-Based Access

A secure, production-ready file uploader that stores files in Backblaze B2 with hash-based naming for deduplication.

## Features

### Core Functionality
- Upload files to Backblaze B2 cloud storage
- SHA256 hash-based file naming (deduplication)
- SQLite metadata storage with indexing
- Beautiful, responsive web UI with drag-and-drop
- Real-time upload progress tracking
- Public file access URLs

### Security & Reliability
- File type validation (blocks dangerous extensions)
- File size limits (configurable, default 50MB)
- Filename sanitization to prevent attacks
- Rate limiting (10 uploads/minute, 50/hour)
- Comprehensive error handling and logging
- Health check endpoint for monitoring
- Duplicate file detection

### User Experience
- Drag-and-drop file upload
- Progress bar with percentage
- Mobile-responsive design
- Clear error messages
- File size formatting
- Instant feedback

## Important: Bucket Configuration

**Your Backblaze B2 bucket must be set to "Public" for file URLs to work!**

Currently, your bucket shows as "Private". To fix this:
1. Go to your Backblaze B2 console
2. Click on "Bucket Settings" for `freeload-uploads`
3. Change "Files in Bucket are:" from "Private" to "Public"
4. Save the changes

## Local Development

1. Clone the repository
2. Copy `.env.example` to `.env` and fill in your Backblaze B2 credentials:
   ```
   B2_KEY_ID=your_key_id
   B2_APPLICATION_KEY=your_application_key
   B2_BUCKET=freeload-uploads
   B2_ENDPOINT=https://s3.us-east-005.backblazeb2.com
   FLASK_SECRET_KEY=your-secret-key-here
   FLASK_ENV=development
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Run the app:
   ```bash
   python app.py
   ```
5. Open http://localhost:5000 in your browser

## Testing

Run the test suite:
```bash
pytest test_app.py
```

## API Endpoints

- `GET /` - Web UI for file upload
- `POST /upload` - Upload a file (multipart/form-data)
  - Returns: `{filename, original_filename, hash, url, file_size, duplicate}`
- `GET /files` - List recent uploads with pagination
  - Query params: `page`, `per_page` (max 100)
- `GET /health` - Health check for monitoring

## Project Structure

```
omniload/
├── app.py           # Main Flask application
├── config.py        # Configuration and environment variables
├── utils.py         # Utility functions (validation, sanitization)
├── test_app.py      # Test suite
├── requirements.txt # Python dependencies
├── railway.json     # Railway deployment config
└── README.md        # This file
```

## Deployment on Railway

### Prerequisites
- A [Railway](https://railway.app) account
- A GitHub account
- Backblaze B2 bucket with appropriate CORS settings and **public visibility**

### Steps

1. **Push to GitHub**
   ```bash
   git init
   git add .
   git commit -m "Initial commit"
   git remote add origin YOUR_GITHUB_REPO_URL
   git push -u origin main
   ```

2. **Deploy on Railway**
   - Go to [railway.app](https://railway.app)
   - Click "New Project"
   - Select "Deploy from GitHub repo"
   - Choose your repository
   - Railway will automatically detect the Python app

3. **Add Environment Variables**
   In Railway dashboard, go to Variables and add:
   - `B2_KEY_ID` - Your Backblaze Key ID
   - `B2_APPLICATION_KEY` - Your Backblaze Application Key
   - `B2_BUCKET` - Your bucket name (freeload-uploads)
   - `B2_ENDPOINT` - Your B2 endpoint (https://s3.us-east-005.backblazeb2.com)
   - `FLASK_SECRET_KEY` - A secure random string
   - `FLASK_ENV` - Set to `production`

4. **Deploy**
   - Railway will automatically deploy your app
   - You'll get a URL like `https://your-app.up.railway.app`

## Configuration

### Environment Variables
- `B2_KEY_ID` - Backblaze B2 Key ID (required)
- `B2_APPLICATION_KEY` - Backblaze B2 Application Key (required)
- `B2_BUCKET` - B2 bucket name (required)
- `B2_ENDPOINT` - B2 S3-compatible endpoint (required)
- `FLASK_SECRET_KEY` - Flask secret key for sessions (required in production)
- `FLASK_ENV` - Environment (development/production)
- `DB_PATH` - SQLite database path (default: metadata.db)

### File Upload Limits
- Maximum file size: 50MB (configurable in `config.py`)
- Allowed extensions: Common document, image, audio, video formats
- Blocked extensions: Executables and potentially dangerous files

## Security Considerations

- All filenames are sanitized to prevent directory traversal attacks
- File extensions are validated against allow/block lists
- Rate limiting prevents abuse
- Uploads are logged with IP addresses
- Consider adding authentication for production use
- Use strong `FLASK_SECRET_KEY` in production
- Enable HTTPS in production (Railway provides this)

## Sprint Progress

- [x] Sprint 1: Basic file upload functionality + Production Polish
  - [x] Core upload/download functionality
  - [x] Security hardening
  - [x] Error handling
  - [x] Rate limiting
  - [x] Testing
  - [x] Logging
  - [x] UI/UX improvements
- [ ] Sprint 2: Hash-based file retrieval
- [ ] Sprint 3: Advanced UI and search
- [ ] Sprint 4: User authentication
- [ ] Sprint 5: Admin dashboard

## Contributing

1. Create a feature branch: `git checkout -b feature-name`
2. Make your changes
3. Run tests: `pytest test_app.py`
4. Commit: `git commit -am 'Add feature'`
5. Push: `git push origin feature-name`
6. Create a Pull Request

## License

MIT License - feel free to use this project for your own purposes. 