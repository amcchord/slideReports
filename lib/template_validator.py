"""
Template validator for detecting malicious patterns in Jinja2 templates.
Provides static analysis to prevent Server-Side Template Injection (SSTI) attacks.
"""
import re
import logging
from typing import Tuple, List, Optional
from jinja2 import TemplateSyntaxError
from .sandbox_config import get_sandbox

logger = logging.getLogger(__name__)


class TemplateValidator:
    """Validates Jinja2 templates for security vulnerabilities"""
    
    # Dangerous patterns that indicate SSTI attempts
    DANGEROUS_PATTERNS = [
        # Python object introspection
        r'__class__',
        r'__mro__',
        r'__subclasses__',
        r'__globals__',
        r'__init__',
        r'__builtins__',
        r'__import__',
        r'__dict__',
        r'__bases__',
        r'__getattribute__',
        r'__getitem__',
        
        # Code execution
        r'\bexec\s*\(',
        r'\beval\s*\(',
        r'\bcompile\s*\(',
        r'\b__import__\s*\(',
        
        # File system access attempts
        r'\bopen\s*\(',
        r'\bfile\s*\(',
        
        # OS module access
        r'\.system\s*\(',
        r'\.popen\s*\(',
        r'\.spawn\s*\(',
        
        # Import attempts
        r'import\s+\w+',
        r'from\s+\w+\s+import',
    ]
    
    # Suspicious but sometimes legitimate patterns (warn but don't reject)
    SUSPICIOUS_PATTERNS = [
        r'\.attr\s*\(',  # attr() filter can be dangerous
        r'\[\s*["\']__',  # Bracket access to dunder attributes
    ]
    
    # Maximum template size (500KB)
    MAX_TEMPLATE_SIZE = 500 * 1024
    
    def __init__(self):
        """Initialize the validator"""
        self.dangerous_regex = [re.compile(pattern, re.IGNORECASE) for pattern in self.DANGEROUS_PATTERNS]
        self.suspicious_regex = [re.compile(pattern, re.IGNORECASE) for pattern in self.SUSPICIOUS_PATTERNS]
    
    def validate(self, html_content: str) -> Tuple[bool, Optional[str], List[str]]:
        """
        Validate a template for security vulnerabilities.
        
        Args:
            html_content: The HTML template content to validate
            
        Returns:
            Tuple of (is_valid, error_message, warnings)
            - is_valid: True if template passes validation
            - error_message: Error message if validation fails, None otherwise
            - warnings: List of warning messages
        """
        warnings = []
        
        # Check template size
        if len(html_content) > self.MAX_TEMPLATE_SIZE:
            return False, f"Template too large ({len(html_content)} bytes). Maximum size is {self.MAX_TEMPLATE_SIZE} bytes.", warnings
        
        # Check for dangerous patterns
        for pattern_regex in self.dangerous_regex:
            match = pattern_regex.search(html_content)
            if match:
                matched_text = match.group(0)
                error_msg = f"Dangerous pattern detected: '{matched_text}'. This pattern is blocked for security reasons."
                logger.warning(f"Template validation failed: {error_msg}")
                return False, error_msg, warnings
        
        # Check for suspicious patterns (warnings only)
        for pattern_regex in self.suspicious_regex:
            match = pattern_regex.search(html_content)
            if match:
                matched_text = match.group(0)
                warning_msg = f"Suspicious pattern detected: '{matched_text}'. This may indicate a security risk."
                warnings.append(warning_msg)
                logger.info(f"Template warning: {warning_msg}")
        
        # Validate Jinja2 syntax
        try:
            sandbox = get_sandbox()
            sandbox.from_string(html_content)
        except TemplateSyntaxError as e:
            error_msg = f"Invalid Jinja2 syntax: {str(e)}"
            logger.warning(f"Template syntax validation failed: {error_msg}")
            return False, error_msg, warnings
        except Exception as e:
            error_msg = f"Template validation error: {str(e)}"
            logger.error(f"Unexpected template validation error: {error_msg}")
            return False, error_msg, warnings
        
        # All checks passed
        return True, None, warnings
    
    def sanitize_content(self, html_content: str) -> str:
        """
        Attempt to sanitize template content by removing dangerous patterns.
        
        Note: This is a best-effort approach. It's better to reject than sanitize.
        
        Args:
            html_content: The HTML template content
            
        Returns:
            Sanitized content (may still be invalid)
        """
        sanitized = html_content
        
        # Replace dangerous patterns with safe placeholders
        for pattern_regex in self.dangerous_regex:
            sanitized = pattern_regex.sub('[BLOCKED_PATTERN]', sanitized)
        
        return sanitized


# Global validator instance
validator = TemplateValidator()


def validate_template(html_content: str) -> Tuple[bool, Optional[str], List[str]]:
    """
    Convenience function to validate a template.
    
    Args:
        html_content: The HTML template content to validate
        
    Returns:
        Tuple of (is_valid, error_message, warnings)
    """
    return validator.validate(html_content)

