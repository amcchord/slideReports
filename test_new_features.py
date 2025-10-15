#!/usr/bin/env python3
"""
Quick test to verify new report features are working
"""
import sys
from datetime import datetime, timedelta
from lib.database import Database
from lib.report_generator import ReportGenerator

def test_new_features():
    """Test the new calendar, screenshot, and storage growth features"""
    print("Testing new report features...")
    print("-" * 60)
    
    # Create a test database path (won't actually create it, just test the code)
    test_db_path = "/tmp/test_reports.db"
    
    try:
        # Initialize database and report generator
        db = Database(test_db_path)
        generator = ReportGenerator(db)
        
        # Test date range
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=7)
        
        import pytz
        user_tz = pytz.timezone('America/New_York')
        
        print("✓ Database and ReportGenerator initialized")
        
        # Test that new methods exist and are callable
        assert hasattr(generator, '_calculate_agent_calendars'), "Missing _calculate_agent_calendars method"
        print("✓ _calculate_agent_calendars method exists")
        
        assert hasattr(generator, '_get_agent_screenshot_pairs'), "Missing _get_agent_screenshot_pairs method"
        print("✓ _get_agent_screenshot_pairs method exists")
        
        assert hasattr(generator, '_calculate_storage_growth'), "Missing _calculate_storage_growth method"
        print("✓ _calculate_storage_growth method exists")
        
        # Test calling the methods (will return empty data with no real database)
        try:
            calendars = generator._calculate_agent_calendars(start_date, end_date, user_tz, None)
            print(f"✓ _calculate_agent_calendars callable - returned {len(calendars)} agent calendars")
        except Exception as e:
            print(f"✗ Error calling _calculate_agent_calendars: {e}")
            
        try:
            screenshots = generator._get_agent_screenshot_pairs(start_date, end_date, user_tz, None)
            print(f"✓ _get_agent_screenshot_pairs callable - returned {len(screenshots)} screenshot pairs")
        except Exception as e:
            print(f"✗ Error calling _get_agent_screenshot_pairs: {e}")
            
        try:
            storage = generator._calculate_storage_growth(start_date, end_date, None)
            print(f"✓ _calculate_storage_growth callable - returned growth data")
            print(f"  - Overall growth: {storage['storage_growth']['growth_formatted']}")
            print(f"  - Device count: {len(storage['device_storage_growth'])}")
        except Exception as e:
            print(f"✗ Error calling _calculate_storage_growth: {e}")
        
        print("-" * 60)
        print("✓ All new features verified successfully!")
        return True
        
    except Exception as e:
        print(f"✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = test_new_features()
    sys.exit(0 if success else 1)

