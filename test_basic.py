#!/usr/bin/env python3
"""
Basic test script to verify Slide Reports System functionality.
Tests encryption, database, API client, and basic operations.
"""
import os
import sys
from dotenv import load_dotenv

# Load environment
load_dotenv()

# Add lib to path
sys.path.insert(0, os.path.dirname(__file__))

from lib.encryption import Encryption
from lib.database import Database, get_database_path
from lib.slide_api import SlideAPIClient
from lib.templates import TemplateManager

# Test configuration
TEST_API_KEY = os.environ.get('TEST_SLIDE_API_KEY', 'tk_hlr3e2d2e7x1_kUqKky4bb3zfefnkKlI8h4GbsNeC8Rx6')
ENCRYPTION_KEY = os.environ.get('ENCRYPTION_KEY')

def test_encryption():
    """Test encryption/decryption"""
    print("Testing Encryption...")
    
    encryption = Encryption(ENCRYPTION_KEY)
    
    # Test encryption
    encrypted = encryption.encrypt(TEST_API_KEY)
    print(f"✓ Encrypted API key: {encrypted[:20]}...")
    
    # Test decryption
    decrypted = encryption.decrypt(encrypted)
    assert decrypted == TEST_API_KEY, "Decryption failed"
    print("✓ Decryption successful")
    
    # Test hash
    hash_val = Encryption.hash_api_key(TEST_API_KEY)
    print(f"✓ API key hash: {hash_val}")
    
    # Test validation
    assert Encryption.validate_api_key_format(TEST_API_KEY), "Validation failed"
    print("✓ API key format validation passed")
    
    print("✓ Encryption tests passed\n")


def test_database():
    """Test database operations"""
    print("Testing Database...")
    
    api_key_hash = Encryption.hash_api_key(TEST_API_KEY)
    db_path = get_database_path(api_key_hash)
    
    # Remove test database if exists
    if os.path.exists(db_path):
        os.remove(db_path)
        print(f"✓ Cleaned up old test database")
    
    # Create database
    db = Database(db_path)
    print("✓ Database initialized")
    
    # Test preferences
    db.set_preference('timezone', 'America/New_York')
    tz = db.get_preference('timezone')
    assert tz == 'America/New_York', "Preference not saved"
    print("✓ Preferences working")
    
    # Test sync status
    db.update_sync_status('devices', 'completed', 5)
    status = db.get_sync_status('devices')
    assert len(status) > 0, "Sync status not saved"
    print("✓ Sync status working")
    
    # Test data insertion
    test_device = {
        'device_id': 'd_test123456',
        'display_name': 'Test Device',
        'hostname': 'test-host',
        'last_seen_at': '2024-01-01T00:00:00Z',
        'raw_json': {'test': 'data'}
    }
    db.upsert_record('devices', 'device_id', test_device)
    devices = db.get_records('devices')
    assert len(devices) == 1, "Device not inserted"
    print(f"✓ Data insertion working ({len(devices)} record)")
    
    # Test data source counts
    counts = db.get_data_source_counts()
    assert counts['devices'] == 1, "Count incorrect"
    print(f"✓ Data source counts working")
    
    print("✓ Database tests passed\n")


def test_api_client():
    """Test API client"""
    print("Testing Slide API Client...")
    
    client = SlideAPIClient(TEST_API_KEY)
    
    # Test connection
    if client.test_connection():
        print("✓ API connection successful")
    else:
        print("✗ API connection failed (key may be invalid)")
        return False
    
    # Test fetching devices (just first page)
    try:
        devices = client._make_request('GET', 'device', params={'limit': 1})
        print(f"✓ API request successful")
        if 'data' in devices:
            print(f"✓ Found {devices.get('pagination', {}).get('total', 0)} total devices")
    except Exception as e:
        print(f"✗ API request failed: {e}")
        return False
    
    print("✓ API client tests passed\n")
    return True


def test_templates():
    """Test template manager"""
    print("Testing Template Manager...")
    
    api_key_hash = Encryption.hash_api_key(TEST_API_KEY)
    tm = TemplateManager(api_key_hash)
    
    # List templates (should have default)
    templates = tm.list_templates()
    assert len(templates) > 0, "No templates found"
    print(f"✓ Found {len(templates)} template(s)")
    
    # Get default template
    default = tm.get_default_template()
    assert default is not None, "Default template not found"
    print(f"✓ Default template: {default['name']}")
    
    print("✓ Template manager tests passed\n")


def main():
    """Run all tests"""
    print("=" * 60)
    print("Slide Reports System - Basic Tests")
    print("=" * 60)
    print()
    
    if not ENCRYPTION_KEY:
        print("✗ ENCRYPTION_KEY not set in environment")
        return False
    
    try:
        test_encryption()
        test_database()
        api_ok = test_api_client()
        test_templates()
        
        print("=" * 60)
        if api_ok:
            print("✓ All tests passed!")
        else:
            print("⚠ Tests passed (API connection failed - check key)")
        print("=" * 60)
        return True
    except Exception as e:
        print(f"\n✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)

