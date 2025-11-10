#!/usr/bin/env python3
"""
Backfill script to update existing snapshot records with correct exists_local,
exists_cloud, and deletion-related columns.

This script parses the locations JSON field and updates the boolean columns
that should have been set during sync.

Usage:
    python3 backfill_snapshot_locations.py [api_key]
    
If no API key is provided, it will process all databases in the data directory.
"""

import os
import sys
import json
import sqlite3
from pathlib import Path
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from lib.database import get_database_path, Database
from lib.encryption import Encryption


def parse_snapshot_locations(locations_json):
    """
    Parse locations JSON and determine exists_local and exists_cloud values.
    
    Args:
        locations_json: JSON string containing locations array
        
    Returns:
        Tuple of (exists_local, exists_cloud)
    """
    exists_local = 0
    exists_cloud = 0
    
    if not locations_json:
        return exists_local, exists_cloud
    
    try:
        locations = json.loads(locations_json)
        if isinstance(locations, list):
            for location in locations:
                if isinstance(location, dict):
                    location_type = location.get('type', '')
                    if location_type == 'local':
                        exists_local = 1
                    elif location_type == 'cloud':
                        exists_cloud = 1
    except json.JSONDecodeError:
        print(f"Warning: Failed to parse locations JSON: {locations_json[:100]}")
    
    return exists_local, exists_cloud


def parse_snapshot_deletions(deletions_json):
    """
    Parse deletions JSON and determine deletion type flags.
    
    Args:
        deletions_json: JSON string containing deletions array
        
    Returns:
        Tuple of (exists_deleted, exists_deleted_retention, exists_deleted_manual, exists_deleted_other)
    """
    exists_deleted = 0
    exists_deleted_retention = 0
    exists_deleted_manual = 0
    exists_deleted_other = 0
    
    if not deletions_json:
        return exists_deleted, exists_deleted_retention, exists_deleted_manual, exists_deleted_other
    
    try:
        deletions = json.loads(deletions_json)
        if isinstance(deletions, list) and deletions:
            exists_deleted = 1
            for deletion in deletions:
                if isinstance(deletion, dict):
                    deletion_type = deletion.get('type', '')
                    if deletion_type == 'retention':
                        exists_deleted_retention = 1
                    elif deletion_type == 'manual':
                        exists_deleted_manual = 1
                    else:
                        exists_deleted_other = 1
    except json.JSONDecodeError:
        print(f"Warning: Failed to parse deletions JSON: {deletions_json[:100]}")
    
    return exists_deleted, exists_deleted_retention, exists_deleted_manual, exists_deleted_other


def backfill_database(db_path, dry_run=False):
    """
    Backfill snapshot location data for a single database.
    
    Args:
        db_path: Path to the SQLite database file
        dry_run: If True, don't actually update the database
        
    Returns:
        Number of records updated
    """
    if not os.path.exists(db_path):
        print(f"Database not found: {db_path}")
        return 0
    
    print(f"\nProcessing database: {db_path}")
    
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Check current schema version
    try:
        cursor.execute("SELECT value FROM schema_metadata WHERE key = 'schema_version'")
        row = cursor.fetchone()
        if row:
            current_version = int(row['value'])
            print(f"Current schema version: {current_version}")
            if current_version >= 1:
                print("Database already at version 1 or higher (snapshot locations should be correct)")
        else:
            print("Current schema version: 0 (pre-versioning)")
    except sqlite3.OperationalError:
        print("Current schema version: 0 (no version table)")
    
    # Check if snapshots table exists
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='snapshots'")
    if not cursor.fetchone():
        print("No snapshots table found, skipping this database")
        conn.close()
        return 0
    
    # Get all snapshots
    cursor.execute("""
        SELECT snapshot_id, locations, deletions, deleted,
               exists_local, exists_cloud, exists_deleted
        FROM snapshots
    """)
    
    snapshots = cursor.fetchall()
    total_snapshots = len(snapshots)
    print(f"Found {total_snapshots} snapshot records")
    
    if total_snapshots == 0:
        conn.close()
        return 0
    
    updated_count = 0
    
    for snapshot in snapshots:
        snapshot_id = snapshot['snapshot_id']
        locations_json = snapshot['locations']
        deletions_json = snapshot['deletions']
        
        # Parse locations
        new_exists_local, new_exists_cloud = parse_snapshot_locations(locations_json)
        
        # Parse deletions
        new_exists_deleted, new_exists_deleted_retention, new_exists_deleted_manual, new_exists_deleted_other = \
            parse_snapshot_deletions(deletions_json)
        
        # Check if update is needed
        needs_update = (
            snapshot['exists_local'] != new_exists_local or
            snapshot['exists_cloud'] != new_exists_cloud or
            snapshot['exists_deleted'] != new_exists_deleted
        )
        
        if needs_update:
            if not dry_run:
                cursor.execute("""
                    UPDATE snapshots 
                    SET exists_local = ?,
                        exists_cloud = ?,
                        exists_deleted = ?,
                        exists_deleted_retention = ?,
                        exists_deleted_manual = ?,
                        exists_deleted_other = ?
                    WHERE snapshot_id = ?
                """, (
                    new_exists_local,
                    new_exists_cloud,
                    new_exists_deleted,
                    new_exists_deleted_retention,
                    new_exists_deleted_manual,
                    new_exists_deleted_other,
                    snapshot_id
                ))
            updated_count += 1
    
    if not dry_run:
        conn.commit()
        print(f"Updated {updated_count} snapshot records")
        
        # Create schema_metadata table if it doesn't exist
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS schema_metadata (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)
        
        # Set schema version to 1 (snapshot locations fixed)
        cursor.execute("""
            INSERT OR REPLACE INTO schema_metadata (key, value, updated_at)
            VALUES ('schema_version', '1', ?)
        """, (datetime.utcnow().isoformat(),))
        conn.commit()
        print("Set database schema version to 1")
    else:
        print(f"Would update {updated_count} snapshot records (dry run)")
    
    conn.close()
    return updated_count


def main():
    """Main entry point for the backfill script."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Backfill snapshot location exists columns'
    )
    parser.add_argument(
        'api_key',
        nargs='?',
        help='API key to backfill (if not provided, processes all databases)'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be updated without actually updating'
    )
    
    args = parser.parse_args()
    
    if args.api_key:
        # Process single database
        api_key_hash = Encryption.hash_api_key(args.api_key)
        db_path = get_database_path(api_key_hash)
        total_updated = backfill_database(db_path, dry_run=args.dry_run)
    else:
        # Process all databases in data directory
        data_dir = os.environ.get('DATA_DIR', '/var/www/reports.slide.recipes/data')
        db_files = list(Path(data_dir).glob('*.db'))
        
        # Filter out template databases
        db_files = [f for f in db_files if not f.name.endswith('_templates.db')]
        
        print(f"Found {len(db_files)} database(s) to process")
        
        total_updated = 0
        for db_file in db_files:
            updated = backfill_database(str(db_file), dry_run=args.dry_run)
            total_updated += updated
    
    print(f"\n{'[DRY RUN] ' if args.dry_run else ''}Total records updated: {total_updated}")
    
    if args.dry_run:
        print("\nRun without --dry-run to apply changes")


if __name__ == '__main__':
    main()

