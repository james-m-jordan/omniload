# 🔌 OmniLoad API Documentation

Complete API reference for OmniLoad v3.0 with metadata and library support.

## Base URL
```
https://your-omniload-instance.com
```

## Authentication
Currently, all endpoints are public. API key authentication is planned for v4.0.

## Core Endpoints

### Upload File
```http
POST /upload
Content-Type: multipart/form-data
```

**Parameters:**
- `file` (required): The file to upload
- `user_hash` (optional): Library hash to group files

**Response:**
```json
{
  "filename": "document.pdf",
  "hash": "a1b2c3d4e5f6...",
  "hash_short": "a1b2c3d4",
  "size": "1.5 MB",
  "url": "https://...",
  "info_url": "/f/a1b2c3d4",
  "user_hash": "abc123def456",
  "library_url": "/library/abc123def456"
}
```

### Get File by Hash
```http
GET /f/{hash}
```

**Parameters:**
- `hash`: Minimum 8 characters of file hash

**Response:** HTML page or redirect to file

### Search Files
```http
GET /search?q={query}
```

**Parameters:**
- `q`: Search query (searches filename, hash, original filename)

**Response:** HTML search results page

### List Recent Files
```http
GET /files
Accept: application/json
```

**Response:**
```json
{
  "files": [
    {
      "id": 1,
      "filename": "document.pdf",
      "original_filename": "My Document.pdf",
      "hash": "a1b2c3d4...",
      "hash_short": "a1b2c3d4",
      "size": "1.5 MB",
      "mime_type": "application/pdf",
      "created_at": "2024-01-01T12:00:00",
      "download_count": 5,
      "description": "Project documentation",
      "tags": [
        {"name": "document", "color": "#10b981"},
        {"name": "work", "color": "#059669"}
      ],
      "info_url": "/f/a1b2c3d4"
    }
  ],
  "count": 50,
  "limit": 50
}
```

### View Library
```http
GET /library/{user_hash}
Accept: application/json
```

**Response:**
```json
{
  "user_hash": "abc123def456",
  "files": [...],
  "total_files": 10
}
```

## Metadata Endpoints

### Get File Metadata
```http
GET /api/files/{id}/metadata
```

**Response:**
```json
{
  "id": 1,
  "filename": "document.pdf",
  "original_filename": "My Document.pdf",
  "hash": "a1b2c3d4...",
  "description": "Project documentation",
  "metadata": {
    "project": "OmniLoad",
    "version": "3.0"
  },
  "size": "1.5 MB",
  "mime_type": "application/pdf",
  "created_at": "2024-01-01T12:00:00",
  "download_count": 5,
  "tags": [
    {"id": 1, "name": "document", "color": "#10b981"}
  ],
  "linked_files": [
    {
      "id": 2,
      "filename": "source.zip",
      "hash": "b2c3d4e5",
      "link_type": "related",
      "description": "Source code"
    }
  ],
  "collections": [
    {"id": 1, "name": "Project Files", "icon": "📁", "color": "#3b82f6"}
  ]
}
```

### Update File Metadata
```http
PUT /api/files/{id}/metadata
Content-Type: application/json
```

**Body:**
```json
{
  "description": "Updated description",
  "metadata": {
    "custom_field": "value"
  }
}
```

**Response:**
```json
{
  "success": true,
  "message": "Metadata updated"
}
```

## Tag Endpoints

### List All Tags
```http
GET /api/tags
```

**Response:**
```json
{
  "tags": [
    {"id": 1, "name": "document", "color": "#10b981"},
    {"id": 2, "name": "image", "color": "#8b5cf6"}
  ]
}
```

### Create Tag
```http
POST /api/tags
Content-Type: application/json
```

**Body:**
```json
{
  "name": "important",
  "color": "#dc2626"
}
```

**Response:**
```json
{
  "id": 9,
  "name": "important",
  "color": "#dc2626"
}
```

### Add Tag to File
```http
POST /api/files/{id}/tags
Content-Type: application/json
```

**Body:**
```json
{
  "tag_id": 1
}
```

### Remove Tag from File
```http
DELETE /api/files/{id}/tags?tag_id={tag_id}
```

## File Link Endpoints

### Create File Link
```http
POST /api/files/{id}/links
Content-Type: application/json
```

**Body:**
```json
{
  "target_file_id": 2,
  "link_type": "related",
  "description": "Source code for this document"
}
```

**Link Types:**
- `related` - General relationship
- `depends_on` - This file depends on target
- `version_of` - This is a version of target
- `part_of` - This is part of target

### Remove File Link
```http
DELETE /api/files/{id}/links?target_file_id={target_id}
```

## Collection Endpoints

### List Collections
```http
GET /api/collections
```

**Response:**
```json
{
  "collections": [
    {
      "id": 1,
      "name": "Project Alpha",
      "description": "All files for Project Alpha",
      "icon": "🚀",
      "color": "#3b82f6",
      "file_count": 15
    }
  ]
}
```

### Create Collection
```http
POST /api/collections
Content-Type: application/json
```

**Body:**
```json
{
  "name": "Project Beta",
  "description": "Development files",
  "icon": "💻",
  "color": "#8b5cf6"
}
```

## Health Check

### System Health
```http
GET /health
```

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2024-01-01T12:00:00.000Z",
  "file_count": 150,
  "version": "3.0.0"
}
```

## Error Responses

All endpoints return consistent error responses:

```json
{
  "error": "Error message here"
}
```

**HTTP Status Codes:**
- `200` - Success
- `201` - Created
- `400` - Bad Request
- `404` - Not Found
- `500` - Internal Server Error

## Rate Limits

Currently no rate limits are enforced. Headers are included for future implementation:

```
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 999
X-RateLimit-Reset: 1640995200
```

## CORS

All endpoints have CORS enabled with:
- `Access-Control-Allow-Origin: *`
- `Access-Control-Allow-Headers: Content-Type`

## Examples

### Upload with cURL
```bash
# Simple upload
curl -X POST -F "file=@document.pdf" https://omniload.com/upload

# Upload to library
curl -X POST -F "file=@document.pdf" -F "user_hash=abc123def456" https://omniload.com/upload
```

### JavaScript Fetch
```javascript
// Get file metadata
const response = await fetch('/api/files/1/metadata');
const metadata = await response.json();

// Update metadata
await fetch('/api/files/1/metadata', {
  method: 'PUT',
  headers: {'Content-Type': 'application/json'},
  body: JSON.stringify({
    description: 'Updated description',
    metadata: {project: 'OmniLoad'}
  })
});

// Add tag
await fetch('/api/files/1/tags', {
  method: 'POST',
  headers: {'Content-Type': 'application/json'},
  body: JSON.stringify({tag_id: 3})
});
```

### Python Requests
```python
import requests

# Upload file
with open('document.pdf', 'rb') as f:
    response = requests.post(
        'https://omniload.com/upload',
        files={'file': f},
        data={'user_hash': 'abc123def456'}
    )
    
# Get library files
response = requests.get(
    'https://omniload.com/library/abc123def456',
    headers={'Accept': 'application/json'}
)
files = response.json()['files']
``` 