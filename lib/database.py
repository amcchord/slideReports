"""
Database schema and management for Slide Reports.
Each user gets their own isolated SQLite database.
"""
import sqlite3
import json
import os
from datetime import datetime
from typing import Optional, Dict, Any, List
from contextlib import contextmanager


class Database:
    """Manage SQLite database for a specific user"""
    
    def __init__(self, db_path: str):
        """
        Initialize database connection.
        
        Args:
            db_path: Path to the SQLite database file
        """
        self.db_path = db_path
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
        """Create all necessary tables if they don't exist"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Schema metadata table for tracking database version and migrations
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS schema_metadata (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)
            
            # Initialize schema version if not exists (0 = pre-versioning, 1 = snapshot locations fixed)
            cursor.execute("""
                INSERT OR IGNORE INTO schema_metadata (key, value, updated_at)
                VALUES ('schema_version', '0', ?)
            """, (datetime.utcnow().isoformat(),))
            
            # User preferences table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_preferences (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)
            
            # Encrypted API key storage for auto-sync
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS encrypted_api_keys (
                    api_key_hash TEXT PRIMARY KEY,
                    encrypted_api_key TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    last_used_at TEXT NOT NULL
                )
            """)
            
            # Set default preferences if not exists
            cursor.execute("""
                INSERT OR IGNORE INTO user_preferences (key, value, updated_at)
                VALUES ('timezone', 'America/New_York', ?)
            """, (datetime.utcnow().isoformat(),))
            
            cursor.execute("""
                INSERT OR IGNORE INTO user_preferences (key, value, updated_at)
                VALUES ('auto_sync_enabled', 'true', ?)
            """, (datetime.utcnow().isoformat(),))
            
            cursor.execute("""
                INSERT OR IGNORE INTO user_preferences (key, value, updated_at)
                VALUES ('auto_sync_frequency_hours', '1', ?)
            """, (datetime.utcnow().isoformat(),))
            
            # Sync status table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS sync_status (
                    resource_type TEXT PRIMARY KEY,
                    last_sync_at TEXT,
                    status TEXT,
                    error_message TEXT,
                    items_synced INTEGER DEFAULT 0
                )
            """)
            
            # Devices table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS devices (
                    device_id TEXT PRIMARY KEY,
                    display_name TEXT,
                    hostname TEXT,
                    last_seen_at TEXT,
                    booted_at TEXT,
                    ip_addresses TEXT,
                    addresses TEXT,
                    public_ip_address TEXT,
                    image_version TEXT,
                    package_version TEXT,
                    storage_used_bytes INTEGER,
                    storage_total_bytes INTEGER,
                    total_agent_included_volume_used_bytes INTEGER,
                    serial_number TEXT,
                    hardware_model_name TEXT,
                    service_model_name TEXT,
                    service_model_name_short TEXT,
                    service_status TEXT,
                    nfr INTEGER,
                    client_id TEXT,
                    synced_at TEXT,
                    raw_json TEXT
                )
            """)
            
            # Agents table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS agents (
                    agent_id TEXT PRIMARY KEY,
                    device_id TEXT,
                    display_name TEXT,
                    hostname TEXT,
                    last_seen_at TEXT,
                    booted_at TEXT,
                    ip_addresses TEXT,
                    addresses TEXT,
                    public_ip_address TEXT,
                    agent_version TEXT,
                    platform TEXT,
                    os TEXT,
                    os_version TEXT,
                    firmware_type TEXT,
                    manufacturer TEXT,
                    encryption_algorithm TEXT,
                    sealed INTEGER,
                    client_id TEXT,
                    passphrases TEXT,
                    vss_writer_configs TEXT,
                    synced_at TEXT,
                    raw_json TEXT
                )
            """)
            
            # Backups table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS backups (
                    backup_id TEXT PRIMARY KEY,
                    agent_id TEXT,
                    started_at TEXT,
                    ended_at TEXT,
                    status TEXT,
                    error_code INTEGER,
                    error_message TEXT,
                    snapshot_id TEXT,
                    synced_at TEXT,
                    raw_json TEXT
                )
            """)
            
            # Snapshots table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS snapshots (
                    snapshot_id TEXT PRIMARY KEY,
                    agent_id TEXT,
                    backup_started_at TEXT,
                    backup_ended_at TEXT,
                    locations TEXT,
                    deleted TEXT,
                    deletions TEXT,
                    verify_boot_status TEXT,
                    verify_boot_screenshot_url TEXT,
                    verify_fs_status TEXT,
                    exists_local INTEGER DEFAULT 0,
                    exists_cloud INTEGER DEFAULT 0,
                    exists_deleted INTEGER DEFAULT 0,
                    exists_deleted_retention INTEGER DEFAULT 0,
                    exists_deleted_manual INTEGER DEFAULT 0,
                    exists_deleted_other INTEGER DEFAULT 0,
                    synced_at TEXT,
                    raw_json TEXT
                )
            """)
            
            # Alerts table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS alerts (
                    alert_id TEXT PRIMARY KEY,
                    alert_type TEXT,
                    alert_fields TEXT,
                    created_at TEXT,
                    resolved INTEGER,
                    resolved_at TEXT,
                    resolved_by TEXT,
                    device_id TEXT,
                    agent_id TEXT,
                    synced_at TEXT,
                    raw_json TEXT
                )
            """)
            
            # Audits table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS audits (
                    audit_id TEXT PRIMARY KEY,
                    audit_time TEXT,
                    account_id TEXT,
                    client_id TEXT,
                    user_id TEXT,
                    system INTEGER,
                    source TEXT,
                    resource_type TEXT,
                    resource_id TEXT,
                    action TEXT,
                    action_fields_json TEXT,
                    description TEXT,
                    synced_at TEXT,
                    raw_json TEXT
                )
            """)
            
            # Clients table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS clients (
                    client_id TEXT PRIMARY KEY,
                    name TEXT,
                    comments TEXT,
                    synced_at TEXT,
                    raw_json TEXT
                )
            """)
            
            # Users table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id TEXT PRIMARY KEY,
                    first_name TEXT,
                    last_name TEXT,
                    display_name TEXT,
                    email TEXT,
                    role_id TEXT,
                    synced_at TEXT,
                    raw_json TEXT
                )
            """)
            
            # Networks table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS networks (
                    network_id TEXT PRIMARY KEY,
                    type TEXT,
                    name TEXT,
                    comments TEXT,
                    client_id TEXT,
                    bridge_device_id TEXT,
                    router_prefix TEXT,
                    dhcp INTEGER,
                    dhcp_range_start TEXT,
                    dhcp_range_end TEXT,
                    nameservers TEXT,
                    internet INTEGER,
                    wg INTEGER,
                    wg_prefix TEXT,
                    wg_public_key TEXT,
                    connected_virt_ids TEXT,
                    ipsec_conns TEXT,
                    port_forwards TEXT,
                    wg_peers TEXT,
                    synced_at TEXT,
                    raw_json TEXT
                )
            """)
            
            # Virtual Machines table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS virtual_machines (
                    virt_id TEXT PRIMARY KEY,
                    device_id TEXT,
                    agent_id TEXT,
                    snapshot_id TEXT,
                    state TEXT,
                    created_at TEXT,
                    expires_at TEXT,
                    cpu_count INTEGER,
                    memory_in_mb INTEGER,
                    disk_bus TEXT,
                    network_model TEXT,
                    network_type TEXT,
                    network_source TEXT,
                    mac_address TEXT,
                    ip_address TEXT,
                    rdp_endpoint TEXT,
                    vnc TEXT,
                    vnc_password TEXT,
                    vnc_enabled INTEGER,
                    purpose TEXT,
                    synced_at TEXT,
                    raw_json TEXT
                )
            """)
            
            # File Restores table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS file_restores (
                    file_restore_id TEXT PRIMARY KEY,
                    device_id TEXT,
                    agent_id TEXT,
                    snapshot_id TEXT,
                    created_at TEXT,
                    expires_at TEXT,
                    synced_at TEXT,
                    raw_json TEXT
                )
            """)
            
            # Image Exports table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS image_exports (
                    image_export_id TEXT PRIMARY KEY,
                    device_id TEXT,
                    agent_id TEXT,
                    snapshot_id TEXT,
                    image_type TEXT,
                    created_at TEXT,
                    nfs INTEGER,
                    nfs_clients TEXT,
                    password TEXT,
                    synced_at TEXT,
                    raw_json TEXT
                )
            """)
            
            # Accounts table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS accounts (
                    account_id TEXT PRIMARY KEY,
                    account_name TEXT,
                    primary_contact TEXT,
                    primary_email TEXT,
                    primary_phone TEXT,
                    billing_address TEXT,
                    alert_emails TEXT,
                    synced_at TEXT,
                    raw_json TEXT
                )
            """)
            
            # Email schedules table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS email_schedules (
                    schedule_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    email_address TEXT NOT NULL,
                    template_id INTEGER NOT NULL,
                    date_range_type TEXT NOT NULL,
                    client_id TEXT,
                    enabled INTEGER DEFAULT 1,
                    attachment_format TEXT DEFAULT 'html',
                    email_subject TEXT,
                    email_body TEXT,
                    schedule_frequency TEXT,
                    schedule_time TEXT,
                    schedule_day_of_week INTEGER,
                    schedule_day_of_month INTEGER,
                    next_run_at TEXT,
                    last_run_at TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)
            
            # Email send log table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS email_send_log (
                    log_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    schedule_id INTEGER,
                    sent_at TEXT NOT NULL,
                    status TEXT NOT NULL,
                    error_message TEXT,
                    recipient_email TEXT NOT NULL,
                    report_date_range TEXT,
                    FOREIGN KEY (schedule_id) REFERENCES email_schedules(schedule_id)
                )
            """)
            
            # Create indexes for common queries
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_backups_agent ON backups(agent_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_backups_started ON backups(started_at)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_snapshots_agent ON snapshots(agent_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_snapshots_backup_started ON snapshots(backup_started_at)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_alerts_device ON alerts(device_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_alerts_agent ON alerts(agent_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_alerts_resolved ON alerts(resolved)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_audits_time ON audits(audit_time)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_agents_device ON agents(device_id)")
            
            # Run migrations for existing databases
            self._migrate_snapshot_location_fields(cursor)
            self._migrate_email_schedules_customization(cursor)
            self._migrate_email_schedules_timing(cursor)
            self._migrate_virtual_machines_vnc_enabled(cursor)
    
    def _migrate_snapshot_location_fields(self, cursor):
        """Add snapshot location fields to existing databases"""
        # Get existing columns in snapshots table
        cursor.execute("PRAGMA table_info(snapshots)")
        existing_columns = [row[1] for row in cursor.fetchall()]
        
        # Add new columns if they don't exist
        if 'exists_local' not in existing_columns:
            cursor.execute("ALTER TABLE snapshots ADD COLUMN exists_local INTEGER DEFAULT 0")
        
        if 'exists_cloud' not in existing_columns:
            cursor.execute("ALTER TABLE snapshots ADD COLUMN exists_cloud INTEGER DEFAULT 0")
        
        if 'exists_deleted' not in existing_columns:
            cursor.execute("ALTER TABLE snapshots ADD COLUMN exists_deleted INTEGER DEFAULT 0")
        
        if 'exists_deleted_retention' not in existing_columns:
            cursor.execute("ALTER TABLE snapshots ADD COLUMN exists_deleted_retention INTEGER DEFAULT 0")
        
        if 'exists_deleted_manual' not in existing_columns:
            cursor.execute("ALTER TABLE snapshots ADD COLUMN exists_deleted_manual INTEGER DEFAULT 0")
        
        if 'exists_deleted_other' not in existing_columns:
            cursor.execute("ALTER TABLE snapshots ADD COLUMN exists_deleted_other INTEGER DEFAULT 0")
    
    def _migrate_email_schedules_customization(self, cursor):
        """Add email customization fields to existing email_schedules table"""
        # Check if email_schedules table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='email_schedules'")
        if not cursor.fetchone():
            return
        
        # Get existing columns in email_schedules table
        cursor.execute("PRAGMA table_info(email_schedules)")
        existing_columns = [row[1] for row in cursor.fetchall()]
        
        # Default email subject and body
        default_subject = "Slide Backup Report - {{ date_range }}"
        default_body = """Your Slide Backup Report for {{ date_range }} is ready.

Executive Summary:
{{ exec_summary }}

Key Metrics:
- Total Backups: {{ total_backups }}
- Success Rate: {{ success_rate }}%

Report generated at {{ generated_at }} ({{ timezone }})"""
        
        # Add new columns if they don't exist
        if 'attachment_format' not in existing_columns:
            cursor.execute("ALTER TABLE email_schedules ADD COLUMN attachment_format TEXT DEFAULT 'pdf'")
        
        if 'email_subject' not in existing_columns:
            cursor.execute("ALTER TABLE email_schedules ADD COLUMN email_subject TEXT")
            # Set default for existing rows
            cursor.execute("UPDATE email_schedules SET email_subject = ? WHERE email_subject IS NULL", (default_subject,))
        
        if 'email_body' not in existing_columns:
            cursor.execute("ALTER TABLE email_schedules ADD COLUMN email_body TEXT")
            # Set default for existing rows
            cursor.execute("UPDATE email_schedules SET email_body = ? WHERE email_body IS NULL", (default_body,))
    
    def _migrate_email_schedules_timing(self, cursor):
        """Add scheduling timing fields to existing email_schedules table"""
        # Check if email_schedules table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='email_schedules'")
        if not cursor.fetchone():
            return
        
        # Get existing columns in email_schedules table
        cursor.execute("PRAGMA table_info(email_schedules)")
        existing_columns = [row[1] for row in cursor.fetchall()]
        
        # Add new scheduling columns if they don't exist
        if 'schedule_frequency' not in existing_columns:
            cursor.execute("ALTER TABLE email_schedules ADD COLUMN schedule_frequency TEXT")
        
        if 'schedule_time' not in existing_columns:
            cursor.execute("ALTER TABLE email_schedules ADD COLUMN schedule_time TEXT")
        
        if 'schedule_day_of_week' not in existing_columns:
            cursor.execute("ALTER TABLE email_schedules ADD COLUMN schedule_day_of_week INTEGER")
        
        if 'schedule_day_of_month' not in existing_columns:
            cursor.execute("ALTER TABLE email_schedules ADD COLUMN schedule_day_of_month INTEGER")
        
        if 'next_run_at' not in existing_columns:
            cursor.execute("ALTER TABLE email_schedules ADD COLUMN next_run_at TEXT")
        
        if 'last_run_at' not in existing_columns:
            cursor.execute("ALTER TABLE email_schedules ADD COLUMN last_run_at TEXT")
    
    def _migrate_virtual_machines_vnc_enabled(self, cursor):
        """Add vnc_enabled field to existing virtual_machines table"""
        # Check if virtual_machines table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='virtual_machines'")
        if not cursor.fetchone():
            return
        
        # Get existing columns in virtual_machines table
        cursor.execute("PRAGMA table_info(virtual_machines)")
        existing_columns = [row[1] for row in cursor.fetchall()]
        
        # Add vnc_enabled column if it doesn't exist
        if 'vnc_enabled' not in existing_columns:
            cursor.execute("ALTER TABLE virtual_machines ADD COLUMN vnc_enabled INTEGER")
    
    def get_preference(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """Get a user preference value"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT value FROM user_preferences WHERE key = ?", (key,))
            row = cursor.fetchone()
            return row['value'] if row else default
    
    def set_preference(self, key: str, value: str):
        """Set a user preference value"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO user_preferences (key, value, updated_at)
                VALUES (?, ?, ?)
            """, (key, value, datetime.utcnow().isoformat()))
    
    def update_sync_status(self, resource_type: str, status: str, 
                          items_synced: int = 0, error_message: Optional[str] = None):
        """Update sync status for a resource type"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO sync_status 
                (resource_type, last_sync_at, status, error_message, items_synced)
                VALUES (?, ?, ?, ?, ?)
            """, (resource_type, datetime.utcnow().isoformat(), status, error_message, items_synced))
    
    def get_sync_status(self, resource_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get sync status for one or all resource types"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            if resource_type:
                cursor.execute("SELECT * FROM sync_status WHERE resource_type = ?", (resource_type,))
            else:
                cursor.execute("SELECT * FROM sync_status ORDER BY resource_type")
            return [dict(row) for row in cursor.fetchall()]
    
    def upsert_record(self, table: str, primary_key: str, data: Dict[str, Any]):
        """Insert or update a record in a table"""
        data['synced_at'] = datetime.utcnow().isoformat()
        data['raw_json'] = json.dumps(data.get('raw_json', {}))
        
        # Convert lists/dicts to JSON strings for storage
        for key, value in data.items():
            if isinstance(value, (list, dict)) and key != 'raw_json':
                data[key] = json.dumps(value)
        
        columns = ', '.join(data.keys())
        placeholders = ', '.join(['?' for _ in data])
        update_clause = ', '.join([f"{k} = excluded.{k}" for k in data.keys()])
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(f"""
                INSERT INTO {table} ({columns})
                VALUES ({placeholders})
                ON CONFLICT({primary_key})
                DO UPDATE SET {update_clause}
            """, list(data.values()))
    
    def get_records(self, table: str, where: Optional[str] = None, 
                   params: Optional[tuple] = None, order_by: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get records from a table"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            query = f"SELECT * FROM {table}"
            if where:
                query += f" WHERE {where}"
            if order_by:
                query += f" ORDER BY {order_by}"
            
            cursor.execute(query, params or ())
            return [dict(row) for row in cursor.fetchall()]
    
    def clear_sync_data(self):
        """
        Clear all synced data from the database while preserving preferences, 
        email schedules, and templates.
        """
        data_tables = [
            'devices', 'agents', 'backups', 'snapshots', 'alerts', 'audits',
            'clients', 'users', 'networks', 'virtual_machines', 'file_restores',
            'image_exports', 'accounts'
        ]
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Delete all data from sync tables
            for table in data_tables:
                cursor.execute(f"DELETE FROM {table}")
            
            # Reset sync status to initial state (not deleted, just reset)
            # This ensures the system knows it needs to sync but isn't stuck in a syncing state
            cursor.execute("""
                UPDATE sync_status 
                SET last_sync_at = NULL, 
                    status = NULL, 
                    error_message = NULL, 
                    items_synced = 0
            """)
    
    def prune_old_snapshots(self, days: int = 90) -> int:
        """
        Delete all snapshot records older than the specified number of days.
        
        Args:
            days: Number of days to keep (default: 90)
            
        Returns:
            Number of records deleted
        """
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        cutoff_iso = cutoff_date.isoformat()
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # First count how many will be deleted
            cursor.execute("""
                SELECT COUNT(*) FROM snapshots 
                WHERE backup_started_at IS NOT NULL 
                AND backup_started_at < ?
            """, (cutoff_iso,))
            count = cursor.fetchone()[0]
            
            # Delete old records
            if count > 0:
                cursor.execute("""
                    DELETE FROM snapshots 
                    WHERE backup_started_at IS NOT NULL 
                    AND backup_started_at < ?
                """, (cutoff_iso,))
            
            return count
    
    def execute_query(self, query: str, params: Optional[tuple] = None) -> List[Dict[str, Any]]:
        """Execute a custom query"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params or ())
            return [dict(row) for row in cursor.fetchall()]
    
    def store_encrypted_api_key(self, api_key_hash: str, encrypted_api_key: str):
        """
        Store an encrypted API key for auto-sync functionality.
        
        Args:
            api_key_hash: Hash of the API key (used as identifier)
            encrypted_api_key: Encrypted API key string
        """
        now = datetime.utcnow().isoformat()
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO encrypted_api_keys 
                (api_key_hash, encrypted_api_key, created_at, last_used_at)
                VALUES (?, ?, ?, ?)
            """, (api_key_hash, encrypted_api_key, now, now))
    
    def get_encrypted_api_key(self, api_key_hash: str) -> Optional[str]:
        """
        Retrieve an encrypted API key for auto-sync.
        
        Args:
            api_key_hash: Hash of the API key
            
        Returns:
            Encrypted API key string or None if not found
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT encrypted_api_key FROM encrypted_api_keys
                WHERE api_key_hash = ?
            """, (api_key_hash,))
            row = cursor.fetchone()
            
            if row:
                # Update last_used_at
                cursor.execute("""
                    UPDATE encrypted_api_keys 
                    SET last_used_at = ?
                    WHERE api_key_hash = ?
                """, (datetime.utcnow().isoformat(), api_key_hash))
                return row['encrypted_api_key']
            
            return None
    
    def get_schema_version(self) -> int:
        """
        Get the current schema version of the database.
        
        Returns:
            Schema version number (0 = pre-versioning)
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute("""
                    SELECT value FROM schema_metadata
                    WHERE key = 'schema_version'
                """)
                row = cursor.fetchone()
                if row:
                    return int(row['value'])
                else:
                    return 0
            except sqlite3.OperationalError:
                # Table doesn't exist in older databases
                return 0
    
    def set_schema_version(self, version: int):
        """
        Set the schema version of the database.
        
        Args:
            version: Schema version number
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO schema_metadata (key, value, updated_at)
                VALUES ('schema_version', ?, ?)
            """, (str(version), datetime.utcnow().isoformat()))
    
    def get_data_source_counts(self) -> Dict[str, int]:
        """Get counts of records in each data source table"""
        tables = [
            'devices', 'agents', 'backups', 'snapshots', 'alerts', 'audits',
            'clients', 'users', 'networks', 'virtual_machines', 
            'file_restores', 'image_exports', 'accounts'
        ]
        
        counts = {}
        with self.get_connection() as conn:
            cursor = conn.cursor()
            for table in tables:
                cursor.execute(f"SELECT COUNT(*) as count FROM {table}")
                counts[table] = cursor.fetchone()['count']
        
        return counts


def get_database_path(api_key_hash: str) -> str:
    """
    Get the database file path for a given API key hash.
    
    Args:
        api_key_hash: Hash of the API key
        
    Returns:
        Path to the SQLite database file
    """
    base_dir = os.environ.get('DATA_DIR', '/var/www/reports.slide.recipes/data')
    return os.path.join(base_dir, f"{api_key_hash}.db")

