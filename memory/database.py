import sqlite3
import json
from pathlib import Path
from typing import Optional,List,Dict,Any
from datetime import datetime
from loguru import logger
from config.settings import settings
from contextlib import contextmanager

class MemoryDatabase:

    def __init__(self,db_path: Optional[str]=None):

        self.db_path = db_path or str(settings.memory_db_path)
        self._init_database()

    @contextmanager
    def get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row

        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"Database error: {e}")
            raise
        finally:
            conn.close()

    def _init_database(self)->None:

        with self.get_connection() as conn:
            cursor = conn.cursor()

            # User preferences table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_preferences (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    key TEXT UNIQUE NOT NULL,
                    value TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Conversation history table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS conversation_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_command TEXT NOT NULL,
                    ai_response TEXT,
                    tools_used TEXT,
                    success BOOLEAN,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Action log table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS action_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    user_command TEXT,
                    selected_tool TEXT NOT NULL,
                    arguments TEXT,
                    result TEXT,
                    success BOOLEAN
                )
            """)
            
            # File paths table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS file_paths (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL,
                    path TEXT NOT NULL,
                    description TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Semantic memory table (for FAISS integration)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS semantic_memory (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    content TEXT NOT NULL,
                    embedding TEXT,
                    metadata TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            logger.info("Database initialized")

    
    def save_preference(self,key:str,value:Any)->bool:

        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT OR REPLACE INTO user_preferences (key, value, updated_at)
                    VALUES (?, ?, CURRENT_TIMESTAMP)
                """, (key, json.dumps(value)))


            logger.info(f"Saved preference: {key}")
            return True

        except Exception as e:
            logger.error(f"Save preference failed: {e}")
            return False

    def get_preference(self,key:str,default:Any=None)->Any:
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT value FROM user_preferences WHERE key = ?",
                    (key,)
                )
                row = cursor.fetchone()

                if row:
                    return json.loads(row['value'])
                return default
        except Exception as e:
            logger.error(f"Get preference failed: {e}")
            return default

    def delete_preference(self,key:str)->bool:
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "DELETE FROM user_preferences WHERE key = ?",
                    (key,)
                )
            
            logger.info(f"Deleted preference: {key}")
            return True
            
        except Exception as e:
            logger.error(f"Delete preference failed: {e}")
            return False

    def save_file_path(
            self,
            name: str,
            path: str,
            description: Optional[str] = None
    )->bool:

        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT OR REPLACE INTO file_paths (name,path,description)
                    VALUES (?,?,?)
                """,(name,path,description))

            logger.info(f"Saved file path: {name} -> {path}")
            return True

        except Exception as e:
            logger.error(f"Save file path failed: {e}")
            return False

    
    def get_file_path(self, name: str) -> Optional[str]:
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT path FROM file_paths WHERE name = ?",
                    (name,)
                )
                row = cursor.fetchone()
                
                if row:
                    return row['path']
                return None
                
        except Exception as e:
            logger.error(f"Get file path failed: {e}")
            return None

    def get_all_file_paths(self)->List[Dict]:
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM file_path")

                return [
                    {
                        'id': row['id'],
                        'name': row['name'],
                        'path': row['path'],
                        'description': row['description']
                    }
                    for row in cursor.fetchall()
                ]

        except Exception as e:
            logger.error(f"Get all file paths failed: {e}")
            return []

    def save_conversation(
            self,
            user_command: str,
            ai_response: str,
            tools_used: List[str],
            success: bool
    )->bool:

        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO conversation_history 
                    (user_command, ai_response, tools_used, success)
                    VALUES (?, ?, ?, ?)
                """,(
                    user_command,
                    ai_response,
                    json.dumps(tools_used),
                    success
                ))

            return True
        except Exception as e:
            logger.error(f"Save conversation failed: {e}")
            return False

    def get_recent_conversations(self,limit: int=10) -> List[Dict]:

        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT * FROM conversation_history 
                    ORDER BY timestamp DESC 
                    LIMIT ?
                """, (limit,))

                return [
                    {
                        'id': row['id'],
                        'user_command': row['user_command'],
                        'ai_response': row['ai_response'],
                        'tools_used': json.loads(row['tools_used']),
                        'success': row['success'],
                        'timestamp': row['timestamp']
                    }
                    for row in cursor.fetchall()
                ]

        except Exception as e:
            logger.error(f"Get conversation failed: {e}")
            return []


    def log_action(
            self,
            user_command: str,
            selected_tool: str,
            arguments: Dict,
            result: str,
            success: bool
    ) -> bool:

        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO action_log 
                    (user_command, selected_tool, arguments, result, success)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    user_command,
                    selected_tool,
                    json.dumps(arguments),
                    result,
                    success
                ))
            return True

        except Exception as e:
            logger.error(f"Log action failed: {e}")
            return False

    
    def get_action_history(self, limit: int = 50) -> List[Dict]:
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT * FROM action_log 
                    ORDER BY timestamp DESC 
                    LIMIT ?
                """, (limit,))
                
                return [
                    {
                        'id': row['id'],
                        'timestamp': row['timestamp'],
                        'user_command': row['user_command'],
                        'selected_tool': row['selected_tool'],
                        'arguments': json.loads(row['arguments']),
                        'result': row['result'],
                        'success': row['success']
                    }
                    for row in cursor.fetchall()
                ]
                
        except Exception as e:
            logger.error(f"Get action history failed: {e}")
            return []
    
    def clear_old_actions(self, days: int = 30) -> int:
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    DELETE FROM action_log 
                    WHERE timestamp < datetime('now', ?)
                """, (f'-{days} days',))
                
                deleted = cursor.rowcount
                logger.info(f"Cleared {deleted} old actions")
                return deleted
                
        except Exception as e:
            logger.error(f"Clear old actions failed: {e}")
            return 0