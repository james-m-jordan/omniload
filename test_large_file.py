#!/usr/bin/env python3
"""Test script for large file uploads"""
import requests
import hashlib
import time
from io import BytesIO

def test_upload(size_mb):
    """Test uploading a file of specified size."""
    print(f"\nTesting {size_mb}MB file upload...")
    
    # Create test data
    data = BytesIO(b'x' * (size_mb * 1024 * 1024))
    
    # Upload
    files = {'file': (f'test_{size_mb}mb.bin', data, 'application/octet-stream')}
    start = time.time()
    
    try:
        r = requests.post("http://localhost:5000/upload", files=files)
        elapsed = time.time() - start
        
        if r.status_code == 200:
            result = r.json()
            print(f"✅ Success! Time: {elapsed:.1f}s, Speed: {size_mb/elapsed:.1f} MB/s")
            print(f"   Hash: {result['hash'][:16]}...")
            print(f"   URL: {result['info_url']}")
            return True
        else:
            print(f"❌ Failed: {r.text}")
            return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

# Test various sizes
print("🧪 Testing OmniLoad Large File Support")
print("=" * 40)

for size in [1, 50, 150]:  # Test up to 150MB (triggers multipart)
    test_upload(size)

print("\n✅ Test complete!") 