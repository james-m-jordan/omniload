#!/usr/bin/env python3
"""
Database migrations for OmniLoad metadata feature.
Run this script to update your database schema.
"""

import sqlite3
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DB_PATH = 'metadata.db'

def run_migration():
    """Run database migrations to add metadata support."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    try:
        # Begin transaction
        conn.execute("BEGIN")
        
        # 0. First ensure files table exists (in case it's a fresh DB)
        logger.info("Ensuring files table exists...")
        c.execute('''CREATE TABLE IF NOT EXISTS files (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT NOT NULL,
            original_filename TEXT,
            filehash TEXT NOT NULL,
            file_size INTEGER,
            mime_type TEXT,
            url TEXT NOT NULL,
            upload_ip TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            download_count INTEGER DEFAULT 0
        )''')
        
        # Create index for faster hash lookups
        c.execute('CREATE INDEX IF NOT EXISTS idx_filehash ON files(filehash)')
        
        # 1. Add description and metadata columns to files table
        logger.info("Adding metadata columns to files table...")
        try:
            c.execute("ALTER TABLE files ADD COLUMN description TEXT")
            logger.info("Added description column")
        except sqlite3.OperationalError:
            logger.info("Description column already exists")
            
        try:
            c.execute("ALTER TABLE files ADD COLUMN metadata_json TEXT")
            logger.info("Added metadata_json column")
        except sqlite3.OperationalError:
            logger.info("Metadata_json column already exists")
            
        try:
            c.execute("ALTER TABLE files ADD COLUMN user_hash TEXT")
            logger.info("Added user_hash column")
        except sqlite3.OperationalError:
            logger.info("User_hash column already exists")
        
        # 2. Create tags table
        logger.info("Creating tags table...")
        c.execute('''CREATE TABLE IF NOT EXISTS tags (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            color TEXT DEFAULT '#3b82f6',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )''')
        
        # 3. Create file_tags junction table
        logger.info("Creating file_tags table...")
        c.execute('''CREATE TABLE IF NOT EXISTS file_tags (
            file_id INTEGER,
            tag_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (file_id, tag_id),
            FOREIGN KEY (file_id) REFERENCES files(id) ON DELETE CASCADE,
            FOREIGN KEY (tag_id) REFERENCES tags(id) ON DELETE CASCADE
        )''')
        
        # 4. Create file_links table for relationships between files
        logger.info("Creating file_links table...")
        c.execute('''CREATE TABLE IF NOT EXISTS file_links (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_file_id INTEGER NOT NULL,
            target_file_id INTEGER NOT NULL,
            link_type TEXT DEFAULT 'related',
            description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (source_file_id) REFERENCES files(id) ON DELETE CASCADE,
            FOREIGN KEY (target_file_id) REFERENCES files(id) ON DELETE CASCADE,
            UNIQUE(source_file_id, target_file_id)
        )''')
        
        # 5. Create collections table for grouping files
        logger.info("Creating collections table...")
        c.execute('''CREATE TABLE IF NOT EXISTS collections (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT,
            icon TEXT DEFAULT '📁',
            color TEXT DEFAULT '#3b82f6',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )''')
        
        # 6. Create file_collections junction table
        logger.info("Creating file_collections table...")
        c.execute('''CREATE TABLE IF NOT EXISTS file_collections (
            file_id INTEGER,
            collection_id INTEGER,
            position INTEGER DEFAULT 0,
            added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (file_id, collection_id),
            FOREIGN KEY (file_id) REFERENCES files(id) ON DELETE CASCADE,
            FOREIGN KEY (collection_id) REFERENCES collections(id) ON DELETE CASCADE
        )''')
        
        # 7. Create indexes for performance
        logger.info("Creating indexes...")
        c.execute("CREATE INDEX IF NOT EXISTS idx_file_tags_file ON file_tags(file_id)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_file_tags_tag ON file_tags(tag_id)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_file_links_source ON file_links(source_file_id)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_file_links_target ON file_links(target_file_id)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_file_collections_file ON file_collections(file_id)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_file_collections_collection ON file_collections(collection_id)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_user_hash ON files(user_hash)")
        
        # 8. Insert some default tags
        logger.info("Inserting default tags...")
        default_tags = [
            ('document', '#10b981'),
            ('image', '#8b5cf6'),
            ('video', '#ef4444'),
            ('code', '#f59e0b'),
            ('archive', '#6b7280'),
            ('important', '#dc2626'),
            ('personal', '#3b82f6'),
            ('work', '#059669'),
        ]
        
        for tag_name, color in default_tags:
            c.execute("INSERT OR IGNORE INTO tags (name, color) VALUES (?, ?)", (tag_name, color))
        
        # Commit transaction
        conn.commit()
        logger.info("✅ Migration completed successfully!")
        
        # Show current schema
        logger.info("\nCurrent tables:")
        c.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        for table in c.fetchall():
            logger.info(f"  - {table[0]}")
            
    except Exception as e:
        conn.rollback()
        logger.error(f"❌ Migration failed: {e}")
        raise
    finally:
        conn.close()

if __name__ == "__main__":
    logger.info("Starting OmniLoad metadata migration...")
    run_migration() 