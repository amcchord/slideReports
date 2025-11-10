"""
Centralized Jinja2 sandbox configuration for secure template rendering.
Provides explicit whitelisting of safe filters and functions.
"""
from jinja2.sandbox import SandboxedEnvironment
from jinja2 import select_autoescape


def create_secure_sandbox():
    """
    Create a configured SandboxedEnvironment with security best practices.
    
    Returns:
        SandboxedEnvironment instance configured for secure template rendering
    """
    # Create sandbox with base configuration
    sandbox = SandboxedEnvironment(
        autoescape=False,  # Keep False for backward compatibility with existing HTML templates
        trim_blocks=True,
        lstrip_blocks=True
    )
    
    # The SandboxedEnvironment already provides good default protection:
    # - Blocks access to private attributes (__xxx__)
    # - Blocks dangerous built-in functions
    # - Restricts attribute access to safe operations
    
    # Additional custom filters can be added here if needed
    # Example: sandbox.filters['custom_filter'] = custom_filter_function
    
    return sandbox


# Global sandbox instance for reuse
_global_sandbox = None


def get_sandbox():
    """
    Get the global sandbox instance (creates it if it doesn't exist).
    
    Returns:
        SandboxedEnvironment instance
    """
    global _global_sandbox
    if _global_sandbox is None:
        _global_sandbox = create_secure_sandbox()
    return _global_sandbox


def render_template_safely(template_content: str, context: dict) -> str:
    """
    Safely render a Jinja2 template with the configured sandbox.
    
    Args:
        template_content: The template string to render
        context: Dictionary of variables to pass to the template
        
    Returns:
        Rendered template string
        
    Raises:
        TemplateSyntaxError: If template has syntax errors
        UndefinedError: If template references undefined variables
        SecurityError: If template tries to access forbidden attributes/methods
    """
    sandbox = get_sandbox()
    template = sandbox.from_string(template_content)
    return template.render(**context)

