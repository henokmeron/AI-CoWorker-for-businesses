"""
Conversation history storage service.
Uses PostgreSQL (Neon) for persistence.
"""
import logging
import json
from typing import List, Optional, Dict, Any
from datetime import datetime
import os

from ..models.conversation import Conversation, Message, ConversationCreate, ConversationUpdate
from ..core.config import settings

# Import psycopg2 for type hints
try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
except ImportError:
    psycopg2 = None
    RealDictCursor = None

logger = logging.getLogger(__name__)


class ConversationService:
    """Service for managing conversation history."""
    
    def __init__(self):
        """Initialize conversation service."""
        # Always initialize JSON storage as fallback
        self._init_json_storage()
        
        # Try to use database if DATABASE_URL is set
        self.db_url = os.getenv("DATABASE_URL") or settings.DATABASE_URL
        self.use_database = bool(self.db_url)
        self.conn = None  # Will be created per request to avoid connection closed errors
        
        if self.use_database:
            try:
                import psycopg2
                from psycopg2.extras import RealDictCursor
                self.psycopg2 = psycopg2
                self.RealDictCursor = RealDictCursor
                # Test connection and initialize tables
                test_conn = psycopg2.connect(self.db_url)
                self._init_database(test_conn)
                test_conn.close()
                logger.info("Using PostgreSQL for conversation storage")
            except Exception as e:
                logger.warning(f"PostgreSQL not available, using JSON fallback: {e}")
                self.use_database = False
                # JSON storage already initialized above
        else:
            logger.info("Using JSON file for conversation storage")
    
    def _get_connection(self):
        """Get a fresh database connection (create new one each time to avoid closed connections)."""
        if not self.use_database or not self.db_url:
            return None
        try:
            return self.psycopg2.connect(self.db_url)
        except Exception as e:
            logger.error(f"Failed to get database connection: {e}")
            return None
    
    def _init_database(self, conn=None):
        """Initialize PostgreSQL tables."""
        if conn is None:
            conn = self._get_connection()
            if conn is None:
                return
            should_close = True
        else:
            should_close = False
        
        try:
            with conn.cursor() as cur:
                # Create conversations table
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS conversations (
                        id VARCHAR(255) PRIMARY KEY,
                        business_id VARCHAR(255) NOT NULL,
                        title TEXT NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        archived BOOLEAN DEFAULT FALSE,
                        tags JSONB DEFAULT '[]'::jsonb,
                        last_local_authority TEXT,
                        last_framework TEXT,
                        last_fee_type TEXT
                    )
                """)
                
                # Create messages table
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS messages (
                        id SERIAL PRIMARY KEY,
                        conversation_id VARCHAR(255) NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
                        role VARCHAR(20) NOT NULL,
                        content TEXT NOT NULL,
                        sources JSONB DEFAULT '[]'::jsonb,
                        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # Create indexes for better performance
                cur.execute("CREATE INDEX IF NOT EXISTS idx_conversations_business ON conversations(business_id)")
                cur.execute("CREATE INDEX IF NOT EXISTS idx_conversations_archived ON conversations(archived)")
                cur.execute("CREATE INDEX IF NOT EXISTS idx_conversations_updated ON conversations(updated_at DESC)")
                cur.execute("CREATE INDEX IF NOT EXISTS idx_messages_conversation ON messages(conversation_id)")
                cur.execute("CREATE INDEX IF NOT EXISTS idx_messages_timestamp ON messages(timestamp)")
                
                conn.commit()
                logger.info("✅ Database tables initialized successfully")
        except Exception as e:
            logger.error(f"❌ Error initializing database: {e}", exc_info=True)
            if should_close and conn:
                conn.close()
            raise RuntimeError(f"Failed to initialize database. Please check your DATABASE_URL and run database_schema.sql in Neon SQL Editor. Error: {e}")
        finally:
            if should_close and conn:
                conn.close()
    
    def _init_json_storage(self):
        """Initialize JSON file storage on persistent volume."""
        import json
        from pathlib import Path
        
        # Use persistent data directory - /app/data on Fly.io
        self.storage_path = Path(settings.DATA_DIR) / "conversations.json"
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Verify directory is writable
        try:
            test_file = self.storage_path.parent / ".test_write"
            test_file.write_text("test")
            test_file.unlink()
        except Exception as e:
            logger.error(f"Storage directory not writable: {e}")
            raise RuntimeError(f"Cannot write to storage directory: {e}")
        
        if not self.storage_path.exists():
            with open(self.storage_path, 'w') as f:
                json.dump([], f)
            logger.info(f"Initialized conversation storage at {self.storage_path}")
    
    def create_conversation(self, business_id: Optional[str] = None, title: Optional[str] = None) -> Conversation:
        """Create a new conversation."""
        # Use default business_id if not provided
        if business_id is None:
            business_id = settings.DEFAULT_BUSINESS_ID
        conv_id = f"conv_{business_id}_{int(datetime.utcnow().timestamp())}"
        title = title or f"Chat {datetime.utcnow().strftime('%Y-%m-%d %H:%M')}"
        
        conversation = Conversation(
            id=conv_id,
            business_id=business_id,
            title=title,
            messages=[],
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        if self.use_database:
            conn = self._get_connection()
            if conn:
                try:
                    with conn.cursor() as cur:
                        cur.execute("""
                            INSERT INTO conversations (id, business_id, title, created_at, updated_at, last_local_authority, last_framework, last_fee_type)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                        """, (conv_id, business_id, title, conversation.created_at, conversation.updated_at, None, None, None))
                        conn.commit()
                    conn.close()
                except Exception as e:
                    logger.error(f"Error saving conversation to database: {e}")
                    if conn:
                        conn.close()
                    self._save_json_conversation(conversation)
            else:
                self._save_json_conversation(conversation)
        else:
            self._save_json_conversation(conversation)
        
        return conversation
    
    def add_message(self, conversation_id: str, message: Message):
        """Add a message to a conversation."""
        if self.use_database:
            conn = self._get_connection()
            if conn:
                try:
                    with conn.cursor() as cur:
                        cur.execute("""
                            INSERT INTO messages (conversation_id, role, content, sources, timestamp)
                            VALUES (%s, %s, %s, %s, %s)
                        """, (conversation_id, message.role, message.content, json.dumps(message.sources), message.timestamp))
                        
                        cur.execute("""
                            UPDATE conversations SET updated_at = CURRENT_TIMESTAMP
                            WHERE id = %s
                        """, (conversation_id,))
                        
                        conn.commit()
                    conn.close()
                except Exception as e:
                    logger.error(f"Error adding message to database: {e}")
                    if conn:
                        conn.close()
                    self._add_json_message(conversation_id, message)
            else:
                self._add_json_message(conversation_id, message)
        else:
            self._add_json_message(conversation_id, message)
    
    def get_conversation(self, conversation_id: str) -> Optional[Conversation]:
        """Get a conversation by ID."""
        if self.use_database and self.RealDictCursor:
            conn = self._get_connection()
            if not conn:
                return self._get_json_conversation(conversation_id)
            try:
                with conn.cursor(cursor_factory=self.RealDictCursor) as cur:
                    cur.execute("SELECT * FROM conversations WHERE id = %s", (conversation_id,))
                    conv_row = cur.fetchone()
                    if not conv_row:
                        return None
                    
                    cur.execute("""
                        SELECT role, content, sources, timestamp
                        FROM messages
                        WHERE conversation_id = %s
                        ORDER BY timestamp ASC
                    """, (conversation_id,))
                    msg_rows = cur.fetchall()
                    
                    messages = [
                        Message(
                            role=msg['role'],
                            content=msg['content'],
                            sources=msg['sources'] if isinstance(msg['sources'], list) else json.loads(msg['sources']),
                            timestamp=msg['timestamp']
                        )
                        for msg in msg_rows
                    ]
                    
                    result = Conversation(
                        id=conv_row['id'],
                        business_id=conv_row['business_id'],
                        title=conv_row['title'],
                        messages=messages,
                        created_at=conv_row['created_at'],
                        updated_at=conv_row['updated_at'],
                        archived=conv_row['archived'],
                        tags=conv_row['tags'] if isinstance(conv_row['tags'], list) else json.loads(conv_row['tags']),
                        last_local_authority=conv_row.get('last_local_authority'),
                        last_framework=conv_row.get('last_framework'),
                        last_fee_type=conv_row.get('last_fee_type')
                    )
                    conn.close()
                    return result
            except Exception as e:
                logger.error(f"Error getting conversation from database: {e}")
                if conn:
                    conn.close()
                return self._get_json_conversation(conversation_id)
        else:
            return self._get_json_conversation(conversation_id)
    
    def list_conversations(self, business_id: Optional[str] = None, archived: Optional[bool] = None) -> List[Conversation]:
        """List conversations for a business (or all conversations if business_id is None)."""
        if self.use_database and self.RealDictCursor:
            conn = self._get_connection()
            if not conn:
                return self._list_json_conversations(business_id, archived)
            try:
                with conn.cursor(cursor_factory=self.RealDictCursor) as cur:
                    if business_id is not None:
                        if archived is not None:
                            cur.execute("""
                                SELECT * FROM conversations
                                WHERE business_id = %s AND archived = %s
                                ORDER BY updated_at DESC
                            """, (business_id, archived))
                        else:
                            cur.execute("""
                                SELECT * FROM conversations
                                WHERE business_id = %s
                                ORDER BY updated_at DESC
                            """, (business_id,))
                    else:
                        if archived is not None:
                            cur.execute("""
                                SELECT * FROM conversations
                                WHERE archived = %s
                                ORDER BY updated_at DESC
                            """, (archived,))
                        else:
                            cur.execute("""
                                SELECT * FROM conversations
                                ORDER BY updated_at DESC
                            """)
                    
                    rows = cur.fetchall()
                    conversations = []
                    for row in rows:
                        cur.execute("""
                            SELECT COUNT(*) as msg_count
                            FROM messages
                            WHERE conversation_id = %s
                        """, (row['id'],))
                        msg_count = cur.fetchone()['msg_count']
                        
                        conversations.append(Conversation(
                            id=row['id'],
                            business_id=row['business_id'],
                            title=row['title'],
                            messages=[],  # Don't load all messages for list
                            created_at=row['created_at'],
                            updated_at=row['updated_at'],
                            archived=row['archived'],
                            tags=row['tags'] if isinstance(row['tags'], list) else json.loads(row['tags'])
                        ))
                    
                    conn.close()
                    return conversations
            except Exception as e:
                logger.error(f"Error listing conversations from database: {e}")
                if conn:
                    conn.close()
                return self._list_json_conversations(business_id, archived)
        else:
            return self._list_json_conversations(business_id, archived)
    
    def archive_conversation(self, conversation_id: str):
        """Archive a conversation."""
        if self.use_database:
            conn = self._get_connection()
            if conn:
                try:
                    with conn.cursor() as cur:
                        cur.execute("""
                            UPDATE conversations SET archived = TRUE, updated_at = CURRENT_TIMESTAMP
                            WHERE id = %s
                        """, (conversation_id,))
                        conn.commit()
                    conn.close()
                except Exception as e:
                    logger.error(f"Error archiving conversation: {e}")
                    if conn:
                        conn.close()
                    self._archive_json_conversation(conversation_id)
            else:
                self._archive_json_conversation(conversation_id)
        else:
            self._archive_json_conversation(conversation_id)
    
    def unarchive_conversation(self, conversation_id: str):
        """Unarchive a conversation."""
        if self.use_database:
            conn = self._get_connection()
            if conn:
                try:
                    with conn.cursor() as cur:
                        cur.execute("""
                            UPDATE conversations SET archived = FALSE, updated_at = CURRENT_TIMESTAMP
                            WHERE id = %s
                        """, (conversation_id,))
                        conn.commit()
                    conn.close()
                except Exception as e:
                    logger.error(f"Error unarchiving conversation: {e}")
                    if conn:
                        conn.close()
                    self._unarchive_json_conversation(conversation_id)
            else:
                self._unarchive_json_conversation(conversation_id)
        else:
            self._unarchive_json_conversation(conversation_id)
    
    def update_conversation(self, conversation_id: str, update: ConversationUpdate) -> Optional[Conversation]:
        """Update a conversation (rename, etc.)."""
        if self.use_database:
            conn = self._get_connection()
            if conn:
                try:
                    with conn.cursor() as cur:
                        updates = []
                        params = []
                        
                        if update.title is not None:
                            updates.append("title = %s")
                            params.append(update.title)
                        
                        if update.archived is not None:
                            updates.append("archived = %s")
                            params.append(update.archived)
                        
                        if update.tags is not None:
                            updates.append("tags = %s")
                            params.append(json.dumps(update.tags))
                        
                        if updates:
                            updates.append("updated_at = CURRENT_TIMESTAMP")
                            params.append(conversation_id)
                            
                            cur.execute(f"""
                                UPDATE conversations SET {', '.join(updates)}
                                WHERE id = %s
                            """, params)
                            conn.commit()
                    conn.close()
                    return self.get_conversation(conversation_id)
                except Exception as e:
                    logger.error(f"Error updating conversation: {e}")
                    if conn:
                        conn.close()
                    return self._update_json_conversation(conversation_id, update)
            else:
                return self._update_json_conversation(conversation_id, update)
        else:
            return self._update_json_conversation(conversation_id, update)
    
    def delete_conversation(self, conversation_id: str):
        """Delete a conversation permanently."""
        if self.use_database:
            conn = self._get_connection()
            if conn:
                try:
                    with conn.cursor() as cur:
                        # Delete messages first (CASCADE should handle this, but being explicit)
                        cur.execute("DELETE FROM messages WHERE conversation_id = %s", (conversation_id,))
                        # Delete conversation
                        cur.execute("DELETE FROM conversations WHERE id = %s", (conversation_id,))
                        conn.commit()
                    conn.close()
                except Exception as e:
                    logger.error(f"Error deleting conversation: {e}")
                    if conn:
                        conn.close()
                    self._delete_json_conversation(conversation_id)
            else:
                self._delete_json_conversation(conversation_id)
        else:
            self._delete_json_conversation(conversation_id)
    
    def _save_json_conversation(self, conversation: Conversation):
        """Save conversation to JSON file."""
        import json
        conversations = self._load_all_json_conversations()
        conversations.append(conversation.dict())
        with open(self.storage_path, 'w') as f:
            json.dump(conversations, f, indent=2, default=str)
    
    def _add_json_message(self, conversation_id: str, message: Message):
        """Add message to JSON storage."""
        import json
        conversations = self._load_all_json_conversations()
        for conv in conversations:
            if conv['id'] == conversation_id:
                conv['messages'].append(message.dict())
                conv['updated_at'] = datetime.utcnow().isoformat()
                break
        with open(self.storage_path, 'w') as f:
            json.dump(conversations, f, indent=2, default=str)
    
    def _get_json_conversation(self, conversation_id: str) -> Optional[Conversation]:
        """Get conversation from JSON storage."""
        conversations = self._load_all_json_conversations()
        for conv_data in conversations:
            if conv_data['id'] == conversation_id:
                # Ensure context fields exist (for backward compatibility)
                if 'last_local_authority' not in conv_data:
                    conv_data['last_local_authority'] = None
                if 'last_framework' not in conv_data:
                    conv_data['last_framework'] = None
                if 'last_fee_type' not in conv_data:
                    conv_data['last_fee_type'] = None
                return Conversation(**conv_data)
        return None
    
    def _list_json_conversations(self, business_id: Optional[str] = None, archived: Optional[bool] = None) -> List[Conversation]:
        """List conversations from JSON storage."""
        conversations = self._load_all_json_conversations()
        result = []
        for conv_data in conversations:
            # Filter by business_id if provided
            if business_id is not None and conv_data['business_id'] != business_id:
                continue
            # Filter by archived status if provided
            if archived is not None and conv_data.get('archived', False) != archived:
                continue
            result.append(Conversation(**conv_data))
        return sorted(result, key=lambda x: x.updated_at, reverse=True)
    
    def _archive_json_conversation(self, conversation_id: str):
        """Archive conversation in JSON storage."""
        import json
        conversations = self._load_all_json_conversations()
        for conv in conversations:
            if conv['id'] == conversation_id:
                conv['archived'] = True
                conv['updated_at'] = datetime.utcnow().isoformat()
                break
        with open(self.storage_path, 'w') as f:
            json.dump(conversations, f, indent=2, default=str)
    
    def _unarchive_json_conversation(self, conversation_id: str):
        """Unarchive conversation in JSON storage."""
        import json
        conversations = self._load_all_json_conversations()
        for conv in conversations:
            if conv['id'] == conversation_id:
                conv['archived'] = False
                conv['updated_at'] = datetime.utcnow().isoformat()
                break
        with open(self.storage_path, 'w') as f:
            json.dump(conversations, f, indent=2, default=str)
    
    def _update_json_conversation(self, conversation_id: str, update: ConversationUpdate) -> Optional[Conversation]:
        """Update conversation in JSON storage."""
        import json
        conversations = self._load_all_json_conversations()
        for conv in conversations:
            if conv['id'] == conversation_id:
                if update.title is not None:
                    conv['title'] = update.title
                if update.archived is not None:
                    conv['archived'] = update.archived
                if update.tags is not None:
                    conv['tags'] = update.tags
                conv['updated_at'] = datetime.utcnow().isoformat()
                with open(self.storage_path, 'w') as f:
                    json.dump(conversations, f, indent=2, default=str)
                return Conversation(**conv)
        return None
    
    def _delete_json_conversation(self, conversation_id: str):
        """Delete conversation from JSON storage."""
        import json
        conversations = self._load_all_json_conversations()
        conversations = [c for c in conversations if c['id'] != conversation_id]
        with open(self.storage_path, 'w') as f:
            json.dump(conversations, f, indent=2, default=str)
    
    def update_conversation_context(
        self, 
        conversation_id: str, 
        last_local_authority: Optional[str] = None,
        last_framework: Optional[str] = None,
        last_fee_type: Optional[str] = None
    ):
        """Update conversation context state for follow-up questions."""
        if self.use_database:
            conn = self._get_connection()
            if conn:
                try:
                    with conn.cursor() as cur:
                        updates = []
                        params = []
                        if last_local_authority is not None:
                            updates.append("last_local_authority = %s")
                            params.append(last_local_authority)
                        if last_framework is not None:
                            updates.append("last_framework = %s")
                            params.append(last_framework)
                        if last_fee_type is not None:
                            updates.append("last_fee_type = %s")
                            params.append(last_fee_type)
                        if updates:
                            params.append(conversation_id)
                            cur.execute(f"""
                                UPDATE conversations SET {', '.join(updates)}, updated_at = CURRENT_TIMESTAMP
                                WHERE id = %s
                            """, params)
                            conn.commit()
                    conn.close()
                except Exception as e:
                    logger.error(f"Error updating conversation context: {e}")
                    if conn:
                        conn.close()
                    self._update_json_conversation_context(conversation_id, last_local_authority, last_framework, last_fee_type)
            else:
                self._update_json_conversation_context(conversation_id, last_local_authority, last_framework, last_fee_type)
        else:
            self._update_json_conversation_context(conversation_id, last_local_authority, last_framework, last_fee_type)
    
    def _update_json_conversation_context(
        self, 
        conversation_id: str,
        last_local_authority: Optional[str] = None,
        last_framework: Optional[str] = None,
        last_fee_type: Optional[str] = None
    ):
        """Update conversation context in JSON storage."""
        import json
        conversations = self._load_all_json_conversations()
        for conv in conversations:
            if conv['id'] == conversation_id:
                if last_local_authority is not None:
                    conv['last_local_authority'] = last_local_authority
                if last_framework is not None:
                    conv['last_framework'] = last_framework
                if last_fee_type is not None:
                    conv['last_fee_type'] = last_fee_type
                conv['updated_at'] = datetime.utcnow().isoformat()
                with open(self.storage_path, 'w') as f:
                    json.dump(conversations, f, indent=2, default=str)
                return
        logger.warning(f"Conversation {conversation_id} not found for context update")
    
    def _load_all_json_conversations(self) -> List[Dict]:
        """Load all conversations from JSON file."""
        import json
        if not self.storage_path.exists():
            return []
        try:
            with open(self.storage_path, 'r') as f:
                return json.load(f)
        except:
            return []


# Global service instance
_conversation_service = None


def get_conversation_service() -> ConversationService:
    """Get global conversation service instance."""
    global _conversation_service
    if _conversation_service is None:
        _conversation_service = ConversationService()
    return _conversation_service

