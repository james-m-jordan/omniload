# 🧠 OmniLoad Context Summary

This file provides context for AI assistants working on this project after a context reset.

## 🎯 Project Overview

**OmniLoad** is a file upload service with hash-based retrieval. Users upload files to Backblaze B2 and get short URLs like `/f/a1b2c3d4` to share them.

## 📍 Current State (After Sprint 2)

### Completed Features
- ✅ File upload with drag-and-drop
- ✅ Hash-based retrieval (`/f/<hash>`)
- ✅ Search by filename or hash
- ✅ Download tracking
- ✅ File info pages
- ✅ SQLite with automatic migrations
- ✅ Deployed on Railway

### Tech Stack
- **Backend**: Python 3.8+, Flask
- **Storage**: Backblaze B2 (private bucket)
- **Database**: SQLite
- **Deployment**: Railway
- **Frontend**: Vanilla JS, inline templates

## 🔐 Important Configuration

### Backblaze B2
- **Bucket**: Must be PRIVATE (not public)
- **URLs**: Constructed as `https://f005.backblazeb2.com/file/BUCKET/KEY`
- **Region Parsing**: Extract from endpoint (e.g., `us-east-005` → `f005`)

### Environment Variables Required
```env
B2_KEY_ID=xxx
B2_APPLICATION_KEY=xxx
B2_BUCKET=xxx
B2_ENDPOINT=https://s3.us-east-005.backblazeb2.com
```

## 🏃 Quick Commands

```bash
# Local development
pip install -r requirements.txt
python app.py

# Deploy to Railway
railway up -d

# Run tests (when added)
pytest test_app.py
```

## 🐛 Known Issues & Solutions

1. **B2 URL Format**: Must preserve leading zeros (f005 not f5)
2. **Database Migrations**: Auto-add columns for backward compatibility
3. **Hash Collisions**: Show disambiguation page for multiple matches

## 📝 Code Patterns

### Adding a New Route
```python
@app.route('/new-feature')
def new_feature():
    try:
        # Database operations
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        # ... queries ...
        conn.close()
        
        # Return template or JSON
        return render_template_string(TEMPLATE, data=data)
    except Exception as e:
        logger.error(f"Error: {e}")
        return jsonify({'error': str(e)}), 500
```

### Database Migration Pattern
```python
# In init_db()
c.execute("PRAGMA table_info(files)")
existing_columns = [column[1] for column in c.fetchall()]

if 'new_column' not in existing_columns:
    c.execute('ALTER TABLE files ADD COLUMN new_column TYPE')
```

## 🚀 Next Steps (Sprint 3+)

### Sprint 3: Enhanced UI & CORS
- File previews (images/videos)
- Bulk upload
- Progress bars
- CORS configuration
- Copy-to-clipboard

### Sprint 4: Security
- Rate limiting
- File validation
- Password protection
- Expiring links
- Admin panel

### Sprint 5: Scale
- CDN integration
- Virus scanning
- Analytics
- API docs

## 💡 Development Philosophy

1. **Ship Fast**: Deploy first, perfect later
2. **User-First**: Every feature should solve a real problem
3. **Simple**: Complexity is added only when necessary
4. **Iterate**: Small improvements compound

## 🔗 Key Files

- `app.py`: Entire application (templates inline)
- `requirements.txt`: Python dependencies
- `railway.json`: Deployment configuration
- `metadata.db`: SQLite database (git-ignored)

## 📚 Resources

- [GitHub Repo](https://github.com/james-m-jordan/omniload)
- [Railway Dashboard](https://railway.app)
- [Backblaze B2 Console](https://secure.backblaze.com/b2_buckets.htm)

---

**For AI Assistants**: This project values speed and iteration. When in doubt, ship it and iterate based on feedback. The codebase is intentionally simple - one file with inline templates. This is by design for rapid development. 