"""
Admin utilities for managing API keys and system data.
"""
import os
import glob
import json
from typing import List, Dict, Any, Optional
from .database import Database, get_database_path


def list_all_api_keys() -> List[Dict[str, Any]]:
    """
    Scan data directory and list all API key hashes with their stats.
    
    Returns:
        List of dictionaries with API key information
    """
    data_dir = os.environ.get('DATA_DIR', '/var/www/reports.slide.recipes/data')
    
    if not os.path.exists(data_dir):
        return []
    
    # Find all main database files
    db_files = glob.glob(os.path.join(data_dir, '*[!_templates].db'))
    
    api_keys = []
    
    for db_path in db_files:
        filename = os.path.basename(db_path)
        if filename.endswith('_templates.db'):
            continue
        
        api_key_hash = filename.replace('.db', '')
        
        try:
            stats = get_key_stats(api_key_hash)
            api_keys.append({
                'hash': api_key_hash,
                'hash_short': api_key_hash[:8],
                **stats
            })
        except Exception as e:
            # If we can't read the database, still show the key
            api_keys.append({
                'hash': api_key_hash,
                'hash_short': api_key_hash[:8],
                'error': str(e),
                'db_size': get_file_size(db_path)
            })
    
    return sorted(api_keys, key=lambda x: x.get('last_sync', ''), reverse=True)


def get_key_stats(api_key_hash: str) -> Dict[str, Any]:
    """
    Get statistics for a specific API key.
    
    Args:
        api_key_hash: Hash of the API key
        
    Returns:
        Dictionary with statistics
    """
    db_path = get_database_path(api_key_hash)
    
    if not os.path.exists(db_path):
        return {'error': 'Database not found'}
    
    db = Database(db_path)
    
    # Get record counts
    counts = db.get_data_source_counts()
    total_records = sum(counts.values())
    
    # Get sync status
    sync_statuses = db.get_sync_status()
    last_sync = None
    for status in sync_statuses:
        if status.get('last_sync_at'):
            if not last_sync or status['last_sync_at'] > last_sync:
                last_sync = status['last_sync_at']
    
    # Get preferences
    auto_sync_enabled = db.get_preference('auto_sync_enabled', 'true').lower() == 'true'
    timezone = db.get_preference('timezone', 'America/New_York')
    
    # Get database size
    db_size = get_file_size(db_path)
    
    # Get templates database size if exists
    templates_path = db_path.replace('.db', '_templates.db')
    templates_size = get_file_size(templates_path) if os.path.exists(templates_path) else 0
    
    return {
        'total_records': total_records,
        'counts': counts,
        'last_sync': last_sync,
        'auto_sync_enabled': auto_sync_enabled,
        'timezone': timezone,
        'db_size': db_size,
        'templates_size': templates_size,
        'total_size': db_size + templates_size
    }


def get_file_size(filepath: str) -> int:
    """Get file size in bytes"""
    try:
        return os.path.getsize(filepath)
    except Exception:
        return 0


def format_bytes(bytes_val: int) -> str:
    """Format bytes for human-readable display"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if bytes_val < 1024.0:
            return f"{bytes_val:.1f} {unit}"
        bytes_val /= 1024.0
    return f"{bytes_val:.1f} TB"


def toggle_auto_sync(api_key_hash: str, enabled: bool) -> bool:
    """
    Toggle auto-sync for a specific API key.
    
    Args:
        api_key_hash: Hash of the API key
        enabled: Whether to enable or disable auto-sync
        
    Returns:
        True if successful
    """
    try:
        db_path = get_database_path(api_key_hash)
        if not os.path.exists(db_path):
            return False
        
        db = Database(db_path)
        db.set_preference('auto_sync_enabled', 'true' if enabled else 'false')
        return True
    except Exception:
        return False


def delete_key_data(api_key_hash: str) -> bool:
    """
    Delete all data for a specific API key.
    
    Args:
        api_key_hash: Hash of the API key
        
    Returns:
        True if successful
    """
    try:
        data_dir = os.environ.get('DATA_DIR', '/var/www/reports.slide.recipes/data')
        
        # Delete main database
        db_path = os.path.join(data_dir, f"{api_key_hash}.db")
        if os.path.exists(db_path):
            os.remove(db_path)
        
        # Delete templates database
        templates_path = os.path.join(data_dir, f"{api_key_hash}_templates.db")
        if os.path.exists(templates_path):
            os.remove(templates_path)
        
        # Delete sync state file
        sync_state_path = os.path.join(data_dir, f"{api_key_hash}_sync_state.json")
        if os.path.exists(sync_state_path):
            os.remove(sync_state_path)
        
        return True
    except Exception as e:
        import logging
        logging.error(f"Error deleting key data: {e}")
        return False


def get_system_stats() -> Dict[str, Any]:
    """Get overall system statistics"""
    api_keys = list_all_api_keys()
    
    total_keys = len(api_keys)
    total_records = sum(key.get('total_records', 0) for key in api_keys)
    total_size = sum(key.get('total_size', 0) for key in api_keys)
    auto_sync_enabled_count = sum(1 for key in api_keys if key.get('auto_sync_enabled', False))
    
    return {
        'total_keys': total_keys,
        'total_records': total_records,
        'total_size': total_size,
        'total_size_formatted': format_bytes(total_size),
        'auto_sync_enabled_count': auto_sync_enabled_count
    }


def list_all_email_schedules() -> List[Dict[str, Any]]:
    """
    List all email schedules across all API keys.
    
    Returns:
        List of dictionaries with schedule information including api_key_hash
    """
    from .email_schedules import EmailScheduleManager
    
    data_dir = os.environ.get('DATA_DIR', '/var/www/reports.slide.recipes/data')
    
    if not os.path.exists(data_dir):
        return []
    
    # Find all main database files
    db_files = glob.glob(os.path.join(data_dir, '*[!_templates].db'))
    
    all_schedules = []
    
    for db_path in db_files:
        filename = os.path.basename(db_path)
        if filename.endswith('_templates.db'):
            continue
        
        api_key_hash = filename.replace('.db', '')
        
        try:
            esm = EmailScheduleManager(db_path)
            schedules = esm.list_schedules()
            
            # Add api_key_hash to each schedule
            for schedule in schedules:
                schedule['api_key_hash'] = api_key_hash
                schedule['api_key_hash_short'] = api_key_hash[:8]
                
                # Add frequency display
                freq = schedule.get('schedule_frequency')
                if freq == 'daily':
                    schedule['frequency_display'] = 'Daily'
                elif freq == 'weekly':
                    days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
                    day_idx = schedule.get('schedule_day_of_week', 0)
                    schedule['frequency_display'] = f"Weekly ({days[day_idx]})"
                elif freq == 'monthly':
                    day = schedule.get('schedule_day_of_month', 1)
                    schedule['frequency_display'] = f"Monthly (Day {day})"
                else:
                    schedule['frequency_display'] = 'Manual'
                
                all_schedules.append(schedule)
        
        except Exception as e:
            import logging
            logging.error(f"Error reading schedules for {api_key_hash[:8]}: {e}")
    
    # Sort by next_run_at
    all_schedules.sort(key=lambda x: x.get('next_run_at') or '9999-99-99', reverse=False)
    
    return all_schedules


def delete_email_schedule(api_key_hash: str, schedule_id: int) -> bool:
    """
    Delete an email schedule for a specific API key.
    
    Args:
        api_key_hash: Hash of the API key
        schedule_id: ID of the schedule to delete
        
    Returns:
        True if successful
    """
    try:
        from .email_schedules import EmailScheduleManager
        
        db_path = get_database_path(api_key_hash)
        if not os.path.exists(db_path):
            return False
        
        esm = EmailScheduleManager(db_path)
        esm.delete_schedule(schedule_id)
        return True
    except Exception as e:
        import logging
        logging.error(f"Error deleting schedule: {e}")
        return False


