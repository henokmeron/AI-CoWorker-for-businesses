"""
User settings storage service.
Uses JSON file storage with PostgreSQL fallback option.
"""
import logging
import json
from typing import Optional, Dict, Any
from datetime import datetime
import os
from pathlib import Path

from ..models.user_settings import UserSettings, UserSettingsUpdate
from ..core.config import settings

logger = logging.getLogger(__name__)


class UserSettingsService:
    """Service for managing user settings."""
    
    def __init__(self):
        """Initialize user settings service."""
        self._init_json_storage()
        
        # Try to use database if DATABASE_URL is set
        self.db_url = os.getenv("DATABASE_URL") or settings.DATABASE_URL
        self.use_database = bool(self.db_url)
        
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
                logger.info("Using PostgreSQL for user settings storage")
            except Exception as e:
                logger.warning(f"PostgreSQL not available, using JSON fallback: {e}")
                self.use_database = False
    
    def _init_json_storage(self):
        """Initialize JSON storage directory."""
        self.json_dir = Path(settings.DATA_DIR) / "user_settings"
        self.json_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"User settings JSON storage initialized at {self.json_dir}")
    
    def _init_database(self, conn):
        """Initialize database tables for user settings."""
        if not self.use_database:
            return
        
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS user_settings (
                        user_id VARCHAR(255) PRIMARY KEY,
                        settings JSONB NOT NULL DEFAULT '{}',
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                conn.commit()
                logger.info("User settings table initialized")
        except Exception as e:
            logger.error(f"Error initializing user settings table: {e}")
            conn.rollback()
            raise
    
    def _get_connection(self):
        """Get database connection."""
        if not self.use_database:
            return None
        try:
            return self.psycopg2.connect(self.db_url)
        except Exception as e:
            logger.error(f"Error connecting to database: {e}")
            return None
    
    def get_settings(self, user_id: str) -> Optional[UserSettings]:
        """Get user settings."""
        if self.use_database:
            conn = self._get_connection()
            if conn:
                try:
                    with conn.cursor(cursor_factory=self.RealDictCursor) as cur:
                        cur.execute("SELECT * FROM user_settings WHERE user_id = %s", (user_id,))
                        row = cur.fetchone()
                        if row:
                            settings_dict = row['settings']
                            settings_dict['user_id'] = user_id
                            settings_dict['created_at'] = row['created_at']
                            settings_dict['updated_at'] = row['updated_at']
                            return UserSettings(**settings_dict)
                    conn.close()
                except Exception as e:
                    logger.error(f"Error getting user settings from database: {e}")
                    if conn:
                        conn.close()
                    return self._get_json_settings(user_id)
            else:
                return self._get_json_settings(user_id)
        else:
            return self._get_json_settings(user_id)
    
    def _get_json_settings(self, user_id: str) -> Optional[UserSettings]:
        """Get user settings from JSON storage."""
        settings_file = self.json_dir / f"{user_id}.json"
        if settings_file.exists():
            try:
                with open(settings_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return UserSettings(**data)
            except Exception as e:
                logger.error(f"Error reading user settings from JSON: {e}")
                return None
        else:
            # Return default settings
            return UserSettings(user_id=user_id)
    
    def update_settings(self, user_id: str, update: UserSettingsUpdate) -> Optional[UserSettings]:
        """Update user settings."""
        # Get existing settings or create new
        existing = self.get_settings(user_id)
        if not existing:
            existing = UserSettings(user_id=user_id)
        
        # Update fields
        update_dict = update.dict(exclude_unset=True)
        existing_dict = existing.dict()
        existing_dict.update(update_dict)
        existing_dict['updated_at'] = datetime.utcnow()
        
        updated_settings = UserSettings(**existing_dict)
        
        # Save
        if self.use_database:
            conn = self._get_connection()
            if conn:
                try:
                    with conn.cursor() as cur:
                        cur.execute("""
                            INSERT INTO user_settings (user_id, settings, updated_at)
                            VALUES (%s, %s, CURRENT_TIMESTAMP)
                            ON CONFLICT (user_id) 
                            DO UPDATE SET settings = %s, updated_at = CURRENT_TIMESTAMP
                        """, (user_id, json.dumps(updated_settings.dict()), json.dumps(updated_settings.dict())))
                        conn.commit()
                    conn.close()
                    return updated_settings
                except Exception as e:
                    logger.error(f"Error updating user settings in database: {e}")
                    if conn:
                        conn.close()
                    return self._save_json_settings(updated_settings)
            else:
                return self._save_json_settings(updated_settings)
        else:
            return self._save_json_settings(updated_settings)
    
    def _save_json_settings(self, settings_obj: UserSettings) -> UserSettings:
        """Save user settings to JSON storage."""
        settings_file = self.json_dir / f"{settings_obj.user_id}.json"
        try:
            with open(settings_file, 'w', encoding='utf-8') as f:
                json.dump(settings_obj.dict(), f, indent=2, default=str)
            return settings_obj
        except Exception as e:
            logger.error(f"Error saving user settings to JSON: {e}")
            raise
    
    def delete_settings(self, user_id: str) -> bool:
        """Delete user settings."""
        if self.use_database:
            conn = self._get_connection()
            if conn:
                try:
                    with conn.cursor() as cur:
                        cur.execute("DELETE FROM user_settings WHERE user_id = %s", (user_id,))
                        conn.commit()
                    conn.close()
                    # Also delete JSON file if exists
                    settings_file = self.json_dir / f"{user_id}.json"
                    if settings_file.exists():
                        settings_file.unlink()
                    return True
                except Exception as e:
                    logger.error(f"Error deleting user settings from database: {e}")
                    if conn:
                        conn.close()
                    return self._delete_json_settings(user_id)
            else:
                return self._delete_json_settings(user_id)
        else:
            return self._delete_json_settings(user_id)
    
    def _delete_json_settings(self, user_id: str) -> bool:
        """Delete user settings from JSON storage."""
        settings_file = self.json_dir / f"{user_id}.json"
        if settings_file.exists():
            try:
                settings_file.unlink()
                return True
            except Exception as e:
                logger.error(f"Error deleting user settings from JSON: {e}")
                return False
        return True


# Global service instance
_user_settings_service = None


def get_user_settings_service() -> UserSettingsService:
    """Get global user settings service instance."""
    global _user_settings_service
    if _user_settings_service is None:
        _user_settings_service = UserSettingsService()
    return _user_settings_service

