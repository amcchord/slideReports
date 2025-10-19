"""
Template management system for storing and managing report templates.
"""
import sqlite3
import os
import json
from datetime import datetime
from typing import Optional, Dict, Any, List
from contextlib import contextmanager
from .builtin_templates import get_builtin_templates, get_builtin_template_by_id


class TemplateManager:
    """Manage report templates for a specific user"""
    
    def __init__(self, api_key_hash: str):
        """
        Initialize template manager.
        
        Args:
            api_key_hash: Hash of the API key for database isolation
        """
        self.api_key_hash = api_key_hash
        base_dir = os.environ.get('DATA_DIR', '/var/www/reports.slide.recipes/data')
        self.db_path = os.path.join(base_dir, f"{api_key_hash}_templates.db")
        self._ensure_directory()
        self._initialize_schema()
    
    def _ensure_directory(self):
        """Ensure the data directory exists"""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
    
    @contextmanager
    def get_connection(self):
        """Context manager for database connections"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
    
    def _initialize_schema(self):
        """Create templates table if it doesn't exist"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS templates (
                    template_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    description TEXT,
                    html_content TEXT NOT NULL,
                    is_default INTEGER DEFAULT 0,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)
            
            # No need to create default templates - using built-in templates instead
    
    def create_template(self, name: str, description: str, html_content: str) -> int:
        """Create a new user template"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            now = datetime.utcnow().isoformat()
            cursor.execute("""
                INSERT INTO templates (name, description, html_content, is_default, created_at, updated_at)
                VALUES (?, ?, ?, 0, ?, ?)
            """, (name, description, html_content, now, now))
            return cursor.lastrowid
    
    def get_template(self, template_id: int) -> Optional[Dict[str, Any]]:
        """
        Get a specific template (built-in or user).
        
        Built-in templates have negative IDs.
        """
        # Convert to int if it's a string (from JSON)
        if isinstance(template_id, str):
            template_id = int(template_id)
        
        # Check if it's a built-in template (negative ID)
        if template_id < 0:
            return get_builtin_template_by_id(template_id)
        
        # Otherwise get from database
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM templates WHERE template_id = ?", (template_id,))
            row = cursor.fetchone()
            if row:
                template = dict(row)
                template['is_builtin'] = False
                return template
            return None
    
    def get_default_template(self) -> Optional[Dict[str, Any]]:
        """Get the default template (always returns built-in Weekly Report)"""
        builtin_templates = get_builtin_templates()
        for template in builtin_templates:
            if template.get('is_default'):
                return template
        # Fallback to first built-in template
        return builtin_templates[0] if builtin_templates else None
    
    def list_templates(self) -> List[Dict[str, Any]]:
        """List all templates (built-in + user templates)"""
        # Get built-in templates
        templates = get_builtin_templates()
        
        # Get user templates from database
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM templates ORDER BY created_at DESC")
            user_templates = [dict(row) for row in cursor.fetchall()]
            
            # Mark user templates as not built-in
            for template in user_templates:
                template['is_builtin'] = False
            
            # Combine: built-in templates first, then user templates
            templates.extend(user_templates)
        
        return templates
    
    def update_template(self, template_id: int, name: Optional[str] = None,
                       description: Optional[str] = None, html_content: Optional[str] = None):
        """
        Update a user template.
        Cannot update built-in templates (negative IDs).
        """
        if template_id < 0:
            raise ValueError("Cannot update built-in templates")
        
        updates = []
        params = []
        
        if name is not None:
            updates.append("name = ?")
            params.append(name)
        
        if description is not None:
            updates.append("description = ?")
            params.append(description)
        
        if html_content is not None:
            updates.append("html_content = ?")
            params.append(html_content)
        
        updates.append("updated_at = ?")
        params.append(datetime.utcnow().isoformat())
        
        params.append(template_id)
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(f"""
                UPDATE templates 
                SET {', '.join(updates)}
                WHERE template_id = ?
            """, params)
    
    def delete_template(self, template_id: int):
        """
        Delete a user template.
        Cannot delete built-in templates (negative IDs).
        """
        if template_id < 0:
            raise ValueError("Cannot delete built-in templates")
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM templates WHERE template_id = ?", (template_id,))
