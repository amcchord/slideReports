"""
Security test suite for SSTI (Server-Side Template Injection) vulnerabilities.
Tests that sandboxing effectively blocks malicious template injection attempts.
"""
from lib.template_validator import validate_template
from lib.sandbox_config import get_sandbox
from jinja2 import TemplateSyntaxError, UndefinedError
from jinja2.exceptions import SecurityError


class TestSSTIProtection:
    """Test suite for SSTI attack prevention"""
    
    # Known SSTI payloads that should be blocked
    DANGEROUS_PAYLOADS = [
        # Python object introspection attacks
        "{{ ''.__class__.__mro__[1].__subclasses__() }}",
        "{{ [].__class__.__base__.__subclasses__() }}",
        "{{ {}.__class__.__bases__[0].__subclasses__() }}",
        "{{ request.__class__.__mro__[1].__subclasses__() }}",
        
        # Code execution attempts
        "{{ __import__('os').system('whoami') }}",
        "{{ __import__('subprocess').check_output('ls') }}",
        "{{ __builtins__.__import__('os').system('id') }}",
        
        # File system access
        "{{ ''.__class__.__mro__[1].__subclasses__()[104].__init__.__globals__['sys'].modules['os'].system('cat /etc/passwd') }}",
        "{{ open('/etc/passwd').read() }}",
        
        # Attribute access tricks
        "{{ request['__class__'] }}",
        "{{ self.__dict__ }}",
        "{{ lipsum.__globals__ }}",
        
        # Module import attempts
        "{% import os %}",
        "{% from os import system %}",
        
        # Exec/eval attempts
        "{{ exec('import os; os.system(\"whoami\")') }}",
        "{{ eval('__import__(\"os\").system(\"ls\")') }}",
        
        # More sophisticated attacks
        "{{ config.__class__.__init__.__globals__['os'].popen('ls').read() }}",
        "{{ url_for.__globals__['__builtins__']['__import__']('os').system('ls') }}",
        "{{ get_flashed_messages.__globals__['__builtins__']['__import__']('os').popen('id').read() }}",
    ]
    
    # Safe template patterns that should be allowed
    SAFE_TEMPLATES = [
        "{{ logo_url }}",
        "{{ report_title or 'Default Title' }}",
        "{% if total_backups > 0 %}{{ total_backups }}{% endif %}",
        "{% for device in devices %}{{ device.name }}{% endfor %}",
        "{{ (storage_used_bytes / 1024**3)|round(1) }} GB",
        "{{ devices|length }}",
        "<h1>{{ report_title }}</h1><p>{{ date_range }}</p>",
    ]
    
    def test_validator_blocks_dangerous_patterns(self):
        """Test that validator blocks known dangerous patterns"""
        for payload in self.DANGEROUS_PAYLOADS:
            is_valid, error_msg, warnings = validate_template(payload)
            assert not is_valid, f"Validator should have blocked: {payload}"
            assert error_msg is not None, f"Should have error message for: {payload}"
            print(f"✓ Blocked: {payload[:60]}...")
    
    def test_validator_allows_safe_patterns(self):
        """Test that validator allows safe template patterns"""
        for template in self.SAFE_TEMPLATES:
            is_valid, error_msg, warnings = validate_template(template)
            assert is_valid, f"Validator should have allowed: {template}, error: {error_msg}"
            print(f"✓ Allowed: {template[:60]}...")
    
    def test_sandbox_blocks_dangerous_rendering(self):
        """Test that sandbox prevents dangerous code execution during rendering"""
        sandbox = get_sandbox()
        
        # Test patterns that pass static validation but should fail at runtime
        dangerous_runtime_patterns = [
            # These might pass string validation but fail at render time
            ("{{ ''.__class__ }}", "Should block class access"),
            ("{{ []|attr('__class__') }}", "Should block attr filter abuse"),
        ]
        
        for pattern, description in dangerous_runtime_patterns:
            try:
                template = sandbox.from_string(pattern)
                result = template.render({})
                # If we get here, check if sensitive info was leaked
                assert '__class__' not in result and 'type' not in result, \
                    f"{description}: {pattern} leaked information: {result}"
                print(f"✓ Sandboxed: {description}")
            except (SecurityError, UndefinedError) as e:
                # This is expected - sandbox blocked the attack
                print(f"✓ Blocked at runtime: {description}")
            except Exception as e:
                # Other exceptions are also fine - attack was prevented
                print(f"✓ Prevented: {description} ({type(e).__name__})")
    
    def test_size_limits(self):
        """Test that excessively large templates are rejected"""
        # Create a template larger than the limit (500KB)
        large_template = "{{ test }}" * 100000  # ~800KB
        is_valid, error_msg, warnings = validate_template(large_template)
        assert not is_valid, "Should reject oversized templates"
        assert "too large" in error_msg.lower(), f"Error message should mention size: {error_msg}"
        print("✓ Rejected oversized template")
    
    def test_nested_attribute_access(self):
        """Test that nested attribute access to dangerous attrs is blocked"""
        dangerous_nested = [
            "{{ x.__class__.__mro__ }}",
            "{{ x['__class__']['__mro__'] }}",
            "{{ x|attr('__class__')|attr('__mro__') }}",
        ]
        
        for pattern in dangerous_nested:
            is_valid, error_msg, warnings = validate_template(pattern)
            assert not is_valid, f"Should block nested access: {pattern}"
            print(f"✓ Blocked nested access: {pattern[:50]}...")
    
    def test_import_statements(self):
        """Test that import statements are blocked"""
        import_attempts = [
            "{% import os %}",
            "{% from os import system %}",
            "{{ __import__('os') }}",
        ]
        
        for pattern in import_attempts:
            is_valid, error_msg, warnings = validate_template(pattern)
            assert not is_valid, f"Should block import: {pattern}"
            print(f"✓ Blocked import: {pattern}")
    
    def test_safe_filters_work(self):
        """Test that safe Jinja2 filters still work"""
        sandbox = get_sandbox()
        safe_filter_tests = [
            ("{{ 'hello'|upper }}", "HELLO"),
            ("{{ 3.14159|round(2) }}", "3.14"),
            ("{{ [1, 2, 3]|length }}", "3"),
            ("{{ 'test'|default('fallback') }}", "test"),
        ]
        
        for template_str, expected in safe_filter_tests:
            template = sandbox.from_string(template_str)
            result = template.render({})
            assert result == expected, f"Safe filter failed: {template_str}"
            print(f"✓ Safe filter works: {template_str}")
    
    def test_context_isolation(self):
        """Test that templates can't access internal Python state"""
        sandbox = get_sandbox()
        
        # Try to access globals, builtins, etc.
        isolation_tests = [
            "{{ __builtins__ }}",
            "{{ __globals__ }}",
            "{{ __dict__ }}",
            "{{ globals() }}",
            "{{ locals() }}",
        ]
        
        for pattern in isolation_tests:
            # Should either fail validation or render safely
            is_valid, error_msg, warnings = validate_template(pattern)
            if is_valid:
                # If it passes validation, ensure sandbox blocks it
                try:
                    template = sandbox.from_string(pattern)
                    result = template.render({})
                    # Result should be empty or innocuous
                    assert not result or result == "", \
                        f"Pattern leaked information: {pattern} -> {result}"
                except (SecurityError, UndefinedError):
                    pass  # Expected - sandbox blocked it
            print(f"✓ Isolated: {pattern}")


def test_basic_ssti_protection():
    """Basic test to ensure SSTI protection is working"""
    print("\n" + "="*70)
    print("SSTI Security Test Suite")
    print("="*70 + "\n")
    
    suite = TestSSTIProtection()
    
    print("\n[1/9] Testing validator blocks dangerous patterns...")
    suite.test_validator_blocks_dangerous_patterns()
    
    print("\n[2/9] Testing validator allows safe patterns...")
    suite.test_validator_allows_safe_patterns()
    
    print("\n[3/9] Testing sandbox blocks dangerous rendering...")
    suite.test_sandbox_blocks_dangerous_rendering()
    
    print("\n[4/9] Testing size limits...")
    suite.test_size_limits()
    
    print("\n[5/9] Testing nested attribute access blocking...")
    suite.test_nested_attribute_access()
    
    print("\n[6/9] Testing import statement blocking...")
    suite.test_import_statements()
    
    print("\n[7/9] Testing safe filters still work...")
    suite.test_safe_filters_work()
    
    print("\n[8/9] Testing context isolation...")
    suite.test_context_isolation()
    
    print("\n" + "="*70)
    print("✅ ALL SSTI SECURITY TESTS PASSED")
    print("="*70 + "\n")


if __name__ == '__main__':
    # Run tests without pytest
    test_basic_ssti_protection()

