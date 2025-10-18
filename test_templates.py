#!/usr/bin/env python3
"""
Test that new templates are created correctly
"""
import sys
import os
import tempfile
from lib.templates import TemplateManager

def test_templates():
    """Test the new template creation"""
    print("Testing new template creation...")
    print("-" * 60)
    
    # Create a temporary database for testing
    temp_dir = tempfile.mkdtemp()
    test_hash = "test_templates_verification"
    
    try:
        # Initialize template manager (will create templates)
        os.environ['DATA_DIR'] = temp_dir
        manager = TemplateManager(test_hash)
        
        print("✓ TemplateManager initialized")
        
        # List all templates
        templates = manager.list_templates()
        print(f"✓ Found {len(templates)} templates")
        
        # Check for our three new templates
        template_names = [t['name'] for t in templates]
        print(f"\nTemplates found:")
        for i, template in enumerate(templates, 1):
            is_default = " (DEFAULT)" if template['is_default'] else ""
            print(f"  {i}. {template['name']}{is_default}")
            print(f"     Description: {template['description']}")
        
        # Verify we have the expected templates
        expected_templates = ['Weekly Report', 'Monthly Report', 'Quarterly Report', 'System Data and Configuration']
        for expected in expected_templates:
            if expected in template_names:
                print(f"✓ Found '{expected}' template")
            else:
                print(f"✗ Missing '{expected}' template")
                return False
        
        # Check that Weekly Report is default
        default_template = [t for t in templates if t['is_default']]
        if default_template:
            print(f"✓ Default template: {default_template[0]['name']}")
            if default_template[0]['name'] == 'Weekly Report':
                print("✓ Weekly Report is correctly set as default")
            else:
                print(f"✗ Wrong default template: {default_template[0]['name']}")
        else:
            print("✗ No default template found")
            return False
        
        # Check that templates include new sections
        weekly_template = [t for t in templates if t['name'] == 'Weekly Report'][0]
        html_content = weekly_template['html_content']
        
        required_sections = [
            'exec_summary',
            'agent_calendars',
            'agent_screenshots',
            'storage_growth',
            'device_storage_growth'
        ]
        
        print("\nChecking Weekly Report template content for variables:")
        for section in required_sections:
            if section in html_content:
                print(f"  ✓ Contains '{section}' variable")
            else:
                print(f"  ✗ Missing '{section}' variable")
                return False
        
        # Check System Data and Configuration template for agent_config_overview
        configs_template = [t for t in templates if t['name'] == 'System Data and Configuration'][0]
        configs_html = configs_template['html_content']
        
        print("\nChecking System Data and Configuration template content for variables:")
        if 'agent_config_overview' in configs_html:
            print(f"  ✓ Contains 'agent_config_overview' variable")
        else:
            print(f"  ✗ Missing 'agent_config_overview' variable")
            return False
        
        # Check for outlier detection features in System Data and Configuration template
        configs_features = ['is_slow_backup', 'is_old_backup', 'config_outlier']
        for feature in configs_features:
            if feature in configs_html:
                print(f"  ✓ Contains '{feature}' feature")
            else:
                print(f"  ✗ Missing '{feature}' feature")
                return False
        
        print("-" * 60)
        print("✓ All templates verified successfully!")
        return True
        
    except Exception as e:
        print(f"✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        # Cleanup
        import shutil
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)

if __name__ == '__main__':
    success = test_templates()
    sys.exit(0 if success else 1)

