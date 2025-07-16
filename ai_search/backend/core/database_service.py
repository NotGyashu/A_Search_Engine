"""
Database Service - Handle all database operations
Clean separation of database logic from business logic
"""

import sqlite3
import time
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from contextlib import contextmanager
import sys

# Add common utilities
sys.path.append(str(Path(__file__).parent.parent.parent))
from common.utils import Logger, PerformanceMonitor, PathManager
from common.config import DATABASE_PATH, DB_TIMEOUT, DB_BATCH_SIZE


class DatabaseService:
    """Handles all database operations for the search engine"""
    
    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or str(PathManager.get_database_path())
        self.logger = Logger.setup_logger("backend.database")
        self._validate_database()
    
    def _validate_database(self):
        """Validate database exists and has required tables"""
        if not Path(self.db_path).exists():
            raise FileNotFoundError(f"Database not found at {self.db_path}")
        
        # Check if required tables exist
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name='documents'
            """)
            if not cursor.fetchone():
                raise ValueError("Database missing required 'documents' table")
    
    @contextmanager
    def get_connection(self):
        """Context manager for database connections"""
        conn = sqlite3.connect(self.db_path, timeout=DB_TIMEOUT)
        conn.row_factory = sqlite3.Row  # Enable dict-like access
        try:
            yield conn
        finally:
            conn.close()
    
    def get_all_documents(self) -> List[Dict]:
        """Get all documents from database"""
        with PerformanceMonitor("Database: Get all documents") as monitor:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT id, url, title, content, domain, word_count, created_at
                    FROM documents 
                    ORDER BY id
                """)
                
                documents = []
                for row in cursor.fetchall():
                    documents.append({
                        'id': row['id'],
                        'url': row['url'],
                        'title': row['title'] or '',
                        'content': row['content'] or '',
                        'domain': row['domain'] or '',
                        'word_count': row['word_count'] or 0,
                        'created_at': row['created_at']
                    })
                
                self.logger.info(f"Retrieved {len(documents)} documents")
                return documents
    
    def get_document_by_id(self, doc_id: int) -> Optional[Dict]:
        """Get a specific document by ID"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, url, title, content, domain, word_count, created_at
                FROM documents 
                WHERE id = ?
            """, (doc_id,))
            
            row = cursor.fetchone()
            if row:
                return {
                    'id': row['id'],
                    'url': row['url'],
                    'title': row['title'] or '',
                    'content': row['content'] or '',
                    'domain': row['domain'] or '',
                    'word_count': row['word_count'] or 0,
                    'created_at': row['created_at']
                }
            return None
    
    def get_documents_by_ids(self, doc_ids: List[int]) -> List[Dict]:
        """Get multiple documents by IDs"""
        if not doc_ids:
            return []
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            placeholders = ','.join(['?' for _ in doc_ids])
            cursor.execute(f"""
                SELECT id, url, title, content, domain, word_count, created_at
                FROM documents 
                WHERE id IN ({placeholders})
                ORDER BY id
            """, doc_ids)
            
            documents = []
            for row in cursor.fetchall():
                documents.append({
                    'id': row['id'],
                    'url': row['url'],
                    'title': row['title'] or '',
                    'content': row['content'] or '',
                    'domain': row['domain'] or '',
                    'word_count': row['word_count'] or 0,
                    'created_at': row['created_at']
                })
            
            return documents
    
    def get_database_stats(self) -> Dict:
        """Get database statistics"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Get document count
            cursor.execute("SELECT COUNT(*) as count FROM documents")
            doc_count = cursor.fetchone()['count']
            
            # Get database size
            cursor.execute("SELECT page_count * page_size as size FROM pragma_page_count(), pragma_page_size()")
            db_size = cursor.fetchone()['size']
            
            # Get average document length
            cursor.execute("SELECT AVG(word_count) as avg_length FROM documents WHERE word_count > 0")
            avg_length = cursor.fetchone()['avg_length'] or 0
            
            # Get domain distribution
            cursor.execute("""
                SELECT domain, COUNT(*) as count 
                FROM documents 
                WHERE domain IS NOT NULL 
                GROUP BY domain 
                ORDER BY count DESC 
                LIMIT 10
            """)
            top_domains = [{'domain': row['domain'], 'count': row['count']} 
                          for row in cursor.fetchall()]
            
            return {
                'total_documents': doc_count,
                'database_size_mb': round(db_size / (1024 * 1024), 2),
                'average_document_length': round(avg_length, 1),
                'top_domains': top_domains,
                'database_path': self.db_path
            }
    
    def search_documents_by_text(self, query: str, limit: int = 100) -> List[Dict]:
        """Simple text search in documents (fallback for when BM25 fails)"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            search_query = f"%{query.lower()}%"
            
            cursor.execute("""
                SELECT id, url, title, content, domain, word_count, created_at
                FROM documents 
                WHERE (LOWER(title) LIKE ? OR LOWER(content) LIKE ?)
                ORDER BY 
                    CASE 
                        WHEN LOWER(title) LIKE ? THEN 1 
                        ELSE 2 
                    END,
                    word_count DESC
                LIMIT ?
            """, (search_query, search_query, search_query, limit))
            
            documents = []
            for row in cursor.fetchall():
                documents.append({
                    'id': row['id'],
                    'url': row['url'],
                    'title': row['title'] or '',
                    'content': row['content'] or '',
                    'domain': row['domain'] or '',
                    'word_count': row['word_count'] or 0,
                    'created_at': row['created_at']
                })
            
            return documents
    
    def health_check(self) -> Dict:
        """Check database health"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) as count FROM documents")
                doc_count = cursor.fetchone()['count']
                
                return {
                    'status': 'healthy',
                    'document_count': doc_count,
                    'database_accessible': True,
                    'database_path': self.db_path
                }
        except Exception as e:
            self.logger.error(f"Database health check failed: {e}")
            return {
                'status': 'unhealthy',
                'error': str(e),
                'database_accessible': False,
                'database_path': self.db_path
            }
