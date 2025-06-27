# OmniLoad - Cloud File Uploader with Hash-Based Access

A simple file uploader that stores files in Backblaze B2 with hash-based naming for deduplication.

## Features

- Upload files to Backblaze B2
- SHA256 hash-based file naming
- SQLite metadata storage
- Simple web UI for uploads
- Public file access URLs

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

4. **Deploy**
   - Railway will automatically deploy your app
   - You'll get a URL like `https://your-app.up.railway.app`

## API Endpoints

- `GET /` - Web UI for file upload
- `POST /upload` - Upload a file (multipart/form-data)
- `GET /files` - List recent uploads (JSON)

## Security Notes

- The current implementation makes all uploaded files publicly accessible
- Consider adding authentication for production use
- Add file size limits and type validation
- Use environment variables for all sensitive data

## Sprint Progress

- [x] Sprint 1: Basic file upload functionality
- [ ] Sprint 2: Hash-based file retrieval
- [ ] Sprint 3: Improved UI and CORS testing
- [ ] Sprint 4: Security and error handling
- [ ] Sprint 5: Documentation and deployment 