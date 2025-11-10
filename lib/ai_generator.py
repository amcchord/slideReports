"""
Claude AI integration for generating report templates.
"""
import anthropic
import json
import logging
from typing import Dict, Any, Optional
from jinja2 import TemplateSyntaxError, UndefinedError
from .sandbox_config import get_sandbox

logger = logging.getLogger(__name__)


class AITemplateGenerator:
    """Generate report templates using Claude AI"""
    
    MODEL = "claude-sonnet-4-20250514"  # Update to actual model name when needed
    
    def __init__(self, api_key: str):
        """
        Initialize AI generator.
        
        Args:
            api_key: Anthropic API key
        """
        self.client = anthropic.Anthropic(api_key=api_key)
        self.template_schema = self._load_template_schema()
    
    def _load_template_schema(self) -> Dict[str, Any]:
        """Load template variable schema for AI context"""
        # This will be loaded from the endpoint or a static file
        # For now, return a comprehensive schema
        return {
            "system": "Jinja2",
            "important_rules": {
                "datetime_handling": "All datetime fields in raw arrays are ISO format STRINGS, not datetime objects. You CANNOT use .days, .seconds, .strftime() directly!",
                "null_safety": "ALWAYS check if a value exists before using it. Use {% if variable %} or {{ variable or 'N/A' }} patterns.",
                "safe_filters": "Use |length (not len()), |default('N/A'), |round for numbers",
                "avoid_complex_operations": "Avoid datetime math, complex selectattr lookups, and Python-specific operations",
                "use_preprocessed_vars": "Prefer using preprocessed variables like agent_backup_status, device_storage instead of raw arrays when possible"
            },
            "available_filters": {
                "length": "Get length: {{ items|length }}",
                "default": "Default value: {{ var|default('N/A') }}",
                "round": "Round numbers: {{ value|round(2) }}",
                "upper": "Uppercase: {{ text|upper }}",
                "lower": "Lowercase: {{ text|lower }}",
                "title": "Title case: {{ text|title }}",
                "join": "Join list: {{ items|join(', ') }}"
            },
            "raw_data_arrays": {
                "devices": "List of all devices with device_id, display_name, hostname, storage_used_bytes, etc.",
                "agents": "List of all agents with agent_id, display_name, hostname, etc.",
                "backups": "List of backups in date range with backup_id, status, started_at (STRING), ended_at (STRING)",
                "snapshots": "List of snapshots in date range with snapshot_id, backup_started_at (STRING), verify_boot_screenshot_url",
                "alerts": "List of alerts in date range with alert_id, alert_type, created_at (STRING), resolved",
                "virtual_machines": "List of VMs with virt_id, state, cpu_count, memory_in_mb",
                "audits": "List of audit entries with audit_id, action, audit_time (STRING)",
                "clients": "List of clients with client_id, name",
                "file_restores": "List of file restores with file_restore_id, created_at (STRING)"
            }
        }
    
    def _test_template(self, html_content: str) -> tuple[bool, Optional[str]]:
        """
        Test if a template can be rendered with sample data.
        Also validates completeness of the HTML structure.
        
        Args:
            html_content: HTML template to test
            
        Returns:
            Tuple of (success: bool, error_message: Optional[str])
        """
        # Check for complete HTML structure
        html_lower = html_content.lower().strip()
        
        # Check if template has proper opening
        has_doctype_or_html = (
            html_lower.startswith('<!doctype html') or 
            html_lower.startswith('<html')
        )
        
        # Check if template has proper closing
        has_closing_html = html_lower.endswith('</html>')
        
        if not has_doctype_or_html:
            return False, "Template doesn't start with <!DOCTYPE html> or <html> - may be incomplete"
        
        if not has_closing_html:
            return False, "Template doesn't end with </html> - appears to be truncated. Try generating again or request a simpler template."
        
        try:
            # Try to create Jinja2 template using sandboxed environment
            sandbox = get_sandbox()
            template = sandbox.from_string(html_content)
            
            # Create minimal sample data
            sample_data = {
                'logo_url': '/static/img/logo.png',
                'report_title': 'Test Report',
                'date_range': '2025-01-01 - 2025-01-07',
                'generated_at': '2025-01-15 10:00:00',
                'timezone': 'America/New_York',
                'client_id': None,
                # Raw data arrays (empty for testing)
                'devices': [],
                'agents': [],
                'backups': [],
                'snapshots': [],
                'alerts': [],
                'virtual_machines': [],
                'audits': [],
                'file_restores': [],
                'clients': [],
                # Preprocessed metrics
                'total_backups': 0,
                'successful_backups': 0,
                'failed_backups': 0,
                'success_rate': 0.0,
                'agent_backup_status': [],
                'active_snapshots': 0,
                'deleted_snapshots': 0,
                'local_snapshots': 0,
                'cloud_snapshots': 0,
                'retention_deleted_count': 0,
                'manually_deleted_count': 0,
                'other_deleted_count': 0,
                'total_alerts': 0,
                'unresolved_alerts': 0,
                'resolved_alerts': 0,
                'device_storage': [],
                'total_vms': 0,
                'running_vms': 0,
                'stopped_vms': 0,
                'agent_calendars': [],
                'agent_screenshots': [],
                'storage_growth': {
                    'start_bytes': 0,
                    'end_bytes': 0,
                    'growth_bytes': 0,
                    'growth_percent': 0,
                    'start_formatted': '0 B',
                    'end_formatted': '0 B',
                    'growth_formatted': '0 B',
                    'is_growth': True
                },
                'device_storage_growth': [],
                # Flags
                'show_backup_stats': True,
                'show_snapshots': True,
                'show_alerts': True,
                'show_storage': True,
                'show_audits': True,
                'show_virtualization': True,
                # Executive summary
                'exec_summary': 'Test summary',
                'executive_summary': 'Test summary'
            }
            
            # Try to render
            template.render(**sample_data)
            return True, None
            
        except TemplateSyntaxError as e:
            return False, f"Template syntax error on line {e.lineno}: {e.message}"
        except UndefinedError as e:
            return False, f"Undefined variable error: {str(e)}"
        except Exception as e:
            return False, f"Template error: {str(e)}"
    
    def generate_template(self, description: str, data_sources: list = None) -> str:
        """
        Generate an HTML report template based on description.
        Tests the template and attempts self-correction if needed.
        
        Args:
            description: Natural language description of desired template
            data_sources: List of data sources that will be available
            
        Returns:
            Generated HTML template string
        """
        data_sources_str = ", ".join(data_sources) if data_sources else "all data sources"
        
        rules_text = "\n".join([f"- {key}: {value}" for key, value in self.template_schema['important_rules'].items()])
        
        system_prompt = f"""You are an expert at creating professional, print-ready HTML report templates using Jinja2.

CRITICAL SAFETY RULES - FOLLOW THESE EXACTLY:
{rules_text}

Generate a complete, self-contained HTML document with embedded CSS that:
1. Is optimized for printing to PDF
2. Has a clean, professional design
3. Uses modern CSS (flexbox, grid) for layouts
4. Includes proper page break handling for printing
5. Has clear section headings and data visualization
6. Uses SAFE Jinja2 template syntax

SAFE VARIABLE USAGE EXAMPLES:
✅ GOOD: {{% if device.storage_used_bytes %}}{{{{ (device.storage_used_bytes / 1024**3)|round(1) }}}} GB{{% else %}}N/A{{% endif %}}
✅ GOOD: {{% for agent in agents[:10] %}} (limit loops)
✅ GOOD: {{{{ variable|default('N/A') }}}}
✅ GOOD: {{{{ devices|length }}}} (use |length, not len())
✅ GOOD: {{{{ variable or 'Default Value' }}}}

❌ BAD: (datetime1 - datetime2).days  (datetime fields are STRINGS!)
❌ BAD: variable.strftime('%Y-%m-%d')  (won't work on strings!)
❌ BAD: agents|selectattr('id', 'equalto', value)|first  (may fail)
❌ BAD: len(devices)  (use devices|length instead)

HOW TO ACCESS DEVICE/AGENT NAMES:
- Device name: {{{{ device.display_name or device.hostname or device.device_id }}}}
- Agent name: {{{{ agent.display_name or agent.hostname or agent.agent_id }}}}
- Always use the 'or' fallback pattern to handle missing display_name

LOOPING THROUGH RAW DATA (when needed):
✅ Devices: {{% for device in devices %}}{{{{ device.display_name or device.hostname }}}}{{% endfor %}}
✅ Agents: {{% for agent in agents %}}{{{{ agent.display_name or agent.hostname }}}}{{% endfor %}}
✅ Backups: {{% for backup in backups %}}{{{{ backup.status }}}} at {{{{ backup.started_at }}}}{{% endfor %}}
✅ Find related: {{% for backup in backups %}}{{% if backup.agent_id == agent.agent_id %}}...{{% endif %}}{{% endfor %}}

PREFER PREPROCESSED VARIABLES (already safe and formatted):
- agent_backup_status (list of agent status objects with name, last_backup, status, duration)
- device_storage (list of storage objects with name, used, total, percent - already formatted)
- agent_calendars (calendar grids per agent)
- agent_screenshots (screenshot pairs per agent)
- Use these instead of raw arrays when possible - they're safer and already formatted!

Common safe variables:
- report_title, date_range, generated_at, timezone (all strings)
- logo_url (string path)
- total_backups, successful_backups, failed_backups, success_rate (numbers)
- show_backup_stats, show_snapshots, show_alerts (booleans)

Available raw arrays (use with caution, check for None):
- devices, agents, backups, snapshots, alerts, virtual_machines, audits, clients, file_restores

Return ONLY the complete HTML document, no explanations."""

        user_prompt = f"""Create an HTML report template based on this description:

{description}

The template will use these data sources: {data_sources_str}

Include SAFE Jinja2 syntax for dynamic content. Make it professional and print-ready.
Remember: datetime fields are STRINGS, always check for None, use preprocessed variables when possible."""

        max_attempts = 3
        for attempt in range(max_attempts):
            try:
                message = self.client.messages.create(
                    model=self.MODEL,
                    max_tokens=16000,  # Increased to allow complete templates with CSS
                    system=system_prompt,
                    messages=[{
                        "role": "user",
                        "content": user_prompt
                    }]
                )
                
                # Extract the HTML from the response
                html_content = message.content[0].text
                
                # Clean up if Claude added markdown code blocks
                if html_content.startswith('```html'):
                    html_content = html_content[7:]
                if html_content.startswith('```'):
                    html_content = html_content[3:]
                if html_content.endswith('```'):
                    html_content = html_content[:-3]
                
                html_content = html_content.strip()
                
                # Check for truncation - template should end with </html>
                if not html_content.lower().endswith('</html>'):
                    logger.warning(f"Template generation may be truncated - doesn't end with </html>. Length: {len(html_content)}")
                    # If on last attempt and truncated, log it but continue
                    if attempt == max_attempts - 1:
                        logger.error("Final attempt still produced truncated template")
                
                # Test the template
                success, error = self._test_template(html_content)
                
                if success:
                    logger.info(f"Template generated successfully on attempt {attempt + 1}")
                    return html_content
                
                # If test failed and we have attempts left, try to fix it
                if attempt < max_attempts - 1:
                    logger.warning(f"Template test failed on attempt {attempt + 1}: {error}. Attempting self-correction...")
                    
                    # Ask AI to fix the error
                    user_prompt = f"""The previous template had this error:

{error}

Please fix the template by following the safety rules more carefully.
Common fixes:
- Check for None values before using them
- Don't use datetime operations on string fields
- Use |default('N/A') for potentially missing values
- Use |length instead of len()
- Limit loops with [:N] syntax

Here's the template that failed:

{html_content}

Return the CORRECTED complete HTML template."""
                else:
                    # Last attempt failed, return it anyway with a warning
                    logger.error(f"Template generation failed after {max_attempts} attempts. Last error: {error}")
                    return html_content
                    
            except Exception as e:
                logger.error(f"AI generation error on attempt {attempt + 1}: {e}")
                if attempt == max_attempts - 1:
                    raise
        
        return html_content
    
    def improve_template(self, current_html: str, improvement_request: str) -> str:
        """
        Improve an existing template based on feedback.
        
        Args:
            current_html: Current HTML template
            improvement_request: Description of desired improvements
            
        Returns:
            Improved HTML template
        """
        system_prompt = """You are an expert at improving HTML report templates.

Given an existing template and improvement requests, modify the HTML to meet the new requirements while maintaining the overall structure and functionality.

Return ONLY the complete improved HTML document, no explanations."""

        user_prompt = f"""Here is the current HTML template:

{current_html}

Please improve it based on this request:

{improvement_request}

Return the complete improved HTML template."""

        message = self.client.messages.create(
            model=self.MODEL,
            max_tokens=24000,  # Increased to allow complete templates with CSS
            system=system_prompt,
            messages=[{
                "role": "user",
                "content": user_prompt
            }]
        )
        
        html_content = message.content[0].text
        
        # Clean up if Claude added markdown code blocks
        if html_content.startswith('```html'):
            html_content = html_content[7:]
        if html_content.startswith('```'):
            html_content = html_content[3:]
        if html_content.endswith('```'):
            html_content = html_content[:-3]
        
        html_content = html_content.strip()
        
        # Check for truncation
        if not html_content.lower().endswith('</html>'):
            logger.warning(f"Improved template may be truncated - doesn't end with </html>. Length: {len(html_content)}")
        
        return html_content
    
    def fix_template_error(self, current_html: str, error_message: str) -> tuple[str, str]:
        """
        Fix a template that has rendering errors.
        
        Args:
            current_html: Current HTML template with errors
            error_message: Error message from template rendering
            
        Returns:
            Tuple of (fixed_html, explanation)
        """
        rules_text = "\n".join([f"- {key}: {value}" for key, value in self.template_schema['important_rules'].items()])
        
        system_prompt = f"""You are an expert at debugging and fixing Jinja2 HTML report templates.

CRITICAL SAFETY RULES - FOLLOW THESE EXACTLY:
{rules_text}

Your task is to identify and fix template errors. Common issues:
1. Undefined variables - check for None before using, use |default('N/A')
2. DateTime operations on strings - remember datetime fields are ISO strings
3. Using len() instead of |length filter
4. Complex selectattr operations that may fail
5. Missing null checks before accessing properties

Return ONLY the fixed HTML template, followed by a separator line "---EXPLANATION---", then a brief explanation of what was fixed."""

        user_prompt = f"""This template has an error:

ERROR: {error_message}

TEMPLATE:
{current_html}

Please fix the error and return:
1. The complete corrected HTML template
2. A line with just "---EXPLANATION---"
3. A brief explanation of what you fixed

Remember: Always check for None, use |default filters, avoid datetime operations on strings."""

        max_attempts = 2
        for attempt in range(max_attempts):
            try:
                message = self.client.messages.create(
                    model=self.MODEL,
                    max_tokens=24000,
                    system=system_prompt,
                    messages=[{
                        "role": "user",
                        "content": user_prompt
                    }]
                )
                
                response_text = message.content[0].text
                
                # Split response into HTML and explanation
                if "---EXPLANATION---" in response_text:
                    parts = response_text.split("---EXPLANATION---", 1)
                    html_content = parts[0].strip()
                    explanation = parts[1].strip()
                else:
                    # No separator found, treat entire response as HTML
                    html_content = response_text
                    explanation = "Template fixed by AI (no explanation provided)"
                
                # Clean up if Claude added markdown code blocks
                if html_content.startswith('```html'):
                    html_content = html_content[7:]
                if html_content.startswith('```'):
                    html_content = html_content[3:]
                if html_content.endswith('```'):
                    html_content = html_content[:-3]
                
                html_content = html_content.strip()
                
                # Check for truncation
                if not html_content.lower().endswith('</html>'):
                    logger.warning(f"Fixed template may be truncated - doesn't end with </html>. Length: {len(html_content)}")
                    if attempt < max_attempts - 1:
                        continue
                
                # Test the fixed template
                success, test_error = self._test_template(html_content)
                
                if success:
                    logger.info(f"Template fixed successfully on attempt {attempt + 1}")
                    return html_content, explanation
                
                # If test failed and we have attempts left, try again
                if attempt < max_attempts - 1:
                    logger.warning(f"Fixed template still has errors on attempt {attempt + 1}: {test_error}")
                    user_prompt = f"""The previous fix didn't work. New error:

ERROR: {test_error}

Original error was: {error_message}

TEMPLATE:
{html_content}

Please fix this more carefully. Return the complete corrected HTML template."""
                else:
                    # Last attempt, return anyway with warning in explanation
                    logger.error(f"Template fix failed after {max_attempts} attempts. Last error: {test_error}")
                    explanation += f"\n\nWarning: Fixed template may still have issues: {test_error}"
                    return html_content, explanation
                    
            except Exception as e:
                logger.error(f"AI fix error on attempt {attempt + 1}: {e}")
                if attempt == max_attempts - 1:
                    raise
        
        return html_content, explanation
    
    def generate_executive_summary(self, metrics_data: Dict[str, Any]) -> str:
        """
        Generate an executive summary based on report metrics.
        
        Args:
            metrics_data: Dictionary of calculated metrics from the report
            
        Returns:
            Generated executive summary text (2-3 paragraphs)
        """
        # Build a summary of the metrics for Claude
        metrics_summary = []
        
        if metrics_data.get('show_backup_stats'):
            metrics_summary.append(f"Backups: {metrics_data.get('total_backups', 0)} total, "
                                 f"{metrics_data.get('success_rate', 0)}% success rate, "
                                 f"{metrics_data.get('failed_backups', 0)} failures")
        
        if metrics_data.get('show_snapshots'):
            metrics_summary.append(f"Snapshots: {metrics_data.get('active_snapshots', 0)} active, "
                                 f"{metrics_data.get('deleted_snapshots', 0)} deleted "
                                 f"({metrics_data.get('retention_deleted_count', 0)} retention, "
                                 f"{metrics_data.get('manually_deleted_count', 0)} manual)")
        
        if metrics_data.get('show_alerts'):
            metrics_summary.append(f"Alerts: {metrics_data.get('unresolved_alerts', 0)} unresolved out of "
                                 f"{metrics_data.get('total_alerts', 0)} total")
        
        if metrics_data.get('show_storage'):
            devices = metrics_data.get('device_storage', [])
            if devices:
                avg_usage = sum(d['percent'] for d in devices) / len(devices)
                metrics_summary.append(f"Storage: {len(devices)} devices monitored, "
                                     f"{avg_usage:.1f}% average usage")
        
        if metrics_data.get('show_virtualization'):
            metrics_summary.append(f"Virtual Machines: {metrics_data.get('total_vms', 0)} total, "
                                 f"{metrics_data.get('running_vms', 0)} running")
        
        date_range = metrics_data.get('date_range', 'the reporting period')
        client_name = metrics_data.get('client_name', '')
        client_context = f" for {client_name}" if client_name else ""
        
        system_prompt = """You are an expert IT analyst writing executive summaries for backup and infrastructure audit reports.

Write a brief, clear narrative (3-5 sentences) that:
1. Tells a cohesive story about the backup environment
2. Highlights the most critical findings
3. Notes any concerns requiring attention
4. Uses professional language suitable for auditors

Write in flowing paragraph form without bullets, lists, or excessive formatting. Be concise and factual."""

        user_prompt = f"""Based on the following backup metrics{client_context} for {date_range}, write a clear 3-5 sentence executive summary as a single flowing paragraph:

{chr(10).join('- ' + item for item in metrics_summary)}

Focus on telling a clear story that an auditor would find valuable. No bullets or lists, just clear prose."""

        message = self.client.messages.create(
            model=self.MODEL,
            max_tokens=300,
            system=system_prompt,
            messages=[{
                "role": "user",
                "content": user_prompt
            }]
        )
        
        return message.content[0].text.strip()

