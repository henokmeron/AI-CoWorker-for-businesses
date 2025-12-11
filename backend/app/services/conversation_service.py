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
        self.use_database = bool(os.getenv("DATABASE_URL"))
        if self.use_database:
            try:
                import psycopg2
                from psycopg2.extras import RealDictCursor
                self.psycopg2 = psycopg2
                self.RealDictCursor = RealDictCursor
                db_url = os.getenv("DATABASE_URL") or settings.DATABASE_URL
                if db_url:
                    self.conn = psycopg2.connect(db_url)
                    self._init_database()
                    logger.info("Using PostgreSQL for conversation storage")
                else:
                    raise ValueError("DATABASE_URL not set")
            except Exception as e:
                logger.warning(f"PostgreSQL not available, using JSON fallback: {e}")
                self.use_database = False
                self._init_json_storage()
        else:
            logger.info("Using JSON file for conversation storage")
            self._init_json_storage()
    
    def _init_database(self):
        """Initialize PostgreSQL tables."""
        try:
            with self.conn.cursor() as cur:
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS conversations (
                        id VARCHAR(255) PRIMARY KEY,
                        business_id VARCHAR(255) NOT NULL,
                        title TEXT NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        archived BOOLEAN DEFAULT FALSE,
                        tags JSONB DEFAULT '[]'::jsonb
                    )
                """)
                
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS messages (
                        id SERIAL PRIMARY KEY,
                        conversation_id VARCHAR(255) REFERENCES conversations(id) ON DELETE CASCADE,
                        role VARCHAR(20) NOT NULL,
                        content TEXT NOT NULL,
                        sources JSONB DEFAULT '[]'::jsonb,
                        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                cur.execute("CREATE INDEX IF NOT EXISTS idx_conversations_business ON conversations(business_id)")
                cur.execute("CREATE INDEX IF NOT EXISTS idx_messages_conversation ON messages(conversation_id)")
                
                self.conn.commit()
                logger.info("Database tables initialized")
        except Exception as e:
            logger.error(f"Error initializing database: {e}")
            self.use_database = False
            self._init_json_storage()
    
    def _init_json_storage(self):
        """Initialize JSON file storage."""
        import json
        from pathlib import Path
        
        self.storage_path = Path(settings.DATA_DIR) / "conversations.json"
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        
        if not self.storage_path.exists():
            with open(self.storage_path, 'w') as f:
                json.dump([], f)
    
    def create_conversation(self, business_id: str, title: Optional[str] = None) -> Conversation:
        """Create a new conversation."""
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
            try:
                with self.conn.cursor() as cur:
                    cur.execute("""
                        INSERT INTO conversations (id, business_id, title, created_at, updated_at)
                        VALUES (%s, %s, %s, %s, %s)
                    """, (conv_id, business_id, title, conversation.created_at, conversation.updated_at))
                    self.conn.commit()
            except Exception as e:
                logger.error(f"Error saving conversation to database: {e}")
                self._save_json_conversation(conversation)
        else:
            self._save_json_conversation(conversation)
        
        return conversation
    
    def add_message(self, conversation_id: str, message: Message):
        """Add a message to a conversation."""
        if self.use_database:
            try:
                with self.conn.cursor() as cur:
                    cur.execute("""
                        INSERT INTO messages (conversation_id, role, content, sources, timestamp)
                        VALUES (%s, %s, %s, %s, %s)
                    """, (conversation_id, message.role, message.content, json.dumps(message.sources), message.timestamp))
                    
                    cur.execute("""
                        UPDATE conversations SET updated_at = CURRENT_TIMESTAMP
                        WHERE id = %s
                    """, (conversation_id,))
                    
                    self.conn.commit()
            except Exception as e:
                logger.error(f"Error adding message to database: {e}")
                self._add_json_message(conversation_id, message)
        else:
            self._add_json_message(conversation_id, message)
    
    def get_conversation(self, conversation_id: str) -> Optional[Conversation]:
        """Get a conversation by ID."""
        if self.use_database and self.RealDictCursor:
            try:
                with self.conn.cursor(cursor_factory=self.RealDictCursor) as cur:
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
                    
                    return Conversation(
                        id=conv_row['id'],
                        business_id=conv_row['business_id'],
                        title=conv_row['title'],
                        messages=messages,
                        created_at=conv_row['created_at'],
                        updated_at=conv_row['updated_at'],
                        archived=conv_row['archived'],
                        tags=conv_row['tags'] if isinstance(conv_row['tags'], list) else json.loads(conv_row['tags'])
                    )
            except Exception as e:
                logger.error(f"Error getting conversation from database: {e}")
                return self._get_json_conversation(conversation_id)
        else:
            return self._get_json_conversation(conversation_id)
    
    def list_conversations(self, business_id: str, archived: Optional[bool] = None) -> List[Conversation]:
        """List conversations for a business."""
        if self.use_database and self.RealDictCursor:
            try:
                with self.conn.cursor(cursor_factory=self.RealDictCursor) as cur:
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
                    
                    return conversations
            except Exception as e:
                logger.error(f"Error listing conversations from database: {e}")
                return self._list_json_conversations(business_id, archived)
        else:
            return self._list_json_conversations(business_id, archived)
    
    def archive_conversation(self, conversation_id: str):
        """Archive a conversation."""
        if self.use_database:
            try:
                with self.conn.cursor() as cur:
                    cur.execute("""
                        UPDATE conversations SET archived = TRUE, updated_at = CURRENT_TIMESTAMP
                        WHERE id = %s
                    """, (conversation_id,))
                    self.conn.commit()
            except Exception as e:
                logger.error(f"Error archiving conversation: {e}")
                self._archive_json_conversation(conversation_id)
        else:
            self._archive_json_conversation(conversation_id)
    
    def unarchive_conversation(self, conversation_id: str):
        """Unarchive a conversation."""
        if self.use_database:
            try:
                with self.conn.cursor() as cur:
                    cur.execute("""
                        UPDATE conversations SET archived = FALSE, updated_at = CURRENT_TIMESTAMP
                        WHERE id = %s
                    """, (conversation_id,))
                    self.conn.commit()
            except Exception as e:
                logger.error(f"Error unarchiving conversation: {e}")
                self._unarchive_json_conversation(conversation_id)
        else:
            self._unarchive_json_conversation(conversation_id)
    
    def update_conversation(self, conversation_id: str, update: ConversationUpdate) -> Optional[Conversation]:
        """Update a conversation (rename, etc.)."""
        if self.use_database:
            try:
                with self.conn.cursor() as cur:
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
                        self.conn.commit()
                        
                        return self.get_conversation(conversation_id)
            except Exception as e:
                logger.error(f"Error updating conversation: {e}")
                return self._update_json_conversation(conversation_id, update)
        else:
            return self._update_json_conversation(conversation_id, update)
    
    def delete_conversation(self, conversation_id: str):
        """Delete a conversation permanently."""
        if self.use_database:
            try:
                with self.conn.cursor() as cur:
                    # Delete messages first (CASCADE should handle this, but being explicit)
                    cur.execute("DELETE FROM messages WHERE conversation_id = %s", (conversation_id,))
                    # Delete conversation
                    cur.execute("DELETE FROM conversations WHERE id = %s", (conversation_id,))
                    self.conn.commit()
            except Exception as e:
                logger.error(f"Error deleting conversation: {e}")
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
                return Conversation(**conv_data)
        return None
    
    def _list_json_conversations(self, business_id: str, archived: Optional[bool] = None) -> List[Conversation]:
        """List conversations from JSON storage."""
        conversations = self._load_all_json_conversations()
        result = []
        for conv_data in conversations:
            if conv_data['business_id'] == business_id:
                if archived is None or conv_data.get('archived', False) == archived:
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

