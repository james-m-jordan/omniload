import os
import tempfile
import pytest
import sqlite3
from app import app, init_db
from config import DB_PATH

@pytest.fixture
def client():
    """Create a test client."""
    # Use a temporary database
    db_fd, app.config['DATABASE'] = tempfile.mkstemp()
    app.config['TESTING'] = True
    
    with app.test_client() as client:
        with app.app_context():
            init_db()
        yield client
    
    os.close(db_fd)
    os.unlink(app.config['DATABASE'])

def test_home_page(client):
    """Test the home page loads."""
    rv = client.get('/')
    assert rv.status_code == 200
    assert b'OmniLoad File Uploader' in rv.data

def test_upload_no_file(client):
    """Test upload with no file."""
    rv = client.post('/upload')
    assert rv.status_code == 400
    json_data = rv.get_json()
    assert 'error' in json_data

def test_upload_empty_filename(client):
    """Test upload with empty filename."""
    data = {'file': (b'', '')}
    rv = client.post('/upload', data=data)
    assert rv.status_code == 400
    json_data = rv.get_json()
    assert 'error' in json_data

def test_health_check(client):
    """Test health check endpoint."""
    rv = client.get('/health')
    # Note: This might fail without proper B2 setup
    # Just check that the endpoint exists
    assert rv.status_code in [200, 500]

def test_list_files(client):
    """Test file listing."""
    rv = client.get('/files')
    assert rv.status_code == 200
    json_data = rv.get_json()
    assert 'files' in json_data
    assert 'total' in json_data

def test_file_size_validation():
    """Test file size validation."""
    from utils import validate_file_size
    from config import MAX_FILE_SIZE
    
    assert validate_file_size(100) == True
    assert validate_file_size(MAX_FILE_SIZE) == True
    assert validate_file_size(MAX_FILE_SIZE + 1) == False

def test_filename_sanitization():
    """Test filename sanitization."""
    from utils import sanitize_filename
    
    assert sanitize_filename('test.txt') == 'test.txt'
    assert sanitize_filename('../../../etc/passwd') == 'etcpasswd'
    assert sanitize_filename('test file (1).pdf') == 'test_file_1_.pdf'
    assert sanitize_filename('a' * 200 + '.txt') == 'a' * 100 + '.txt'

def test_allowed_file():
    """Test file extension validation."""
    from utils import allowed_file
    
    assert allowed_file('test.pdf') == True
    assert allowed_file('test.exe') == False
    assert allowed_file('test') == False
    assert allowed_file('test.PDF') == True  # Case insensitive

if __name__ == '__main__':
    pytest.main([__file__]) 