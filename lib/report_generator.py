"""
Report generation engine for creating reports from templates and data.
"""
import pytz
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from jinja2 import Template
from .database import Database


def format_datetime_friendly(dt: Optional[datetime], tz: pytz.timezone) -> str:
    """
    Format datetime in a human-friendly way.
    
    Args:
        dt: Datetime to format
        tz: User's timezone
        
    Returns:
        Human-friendly date string (e.g., "3 hours ago", "January 15, 2025")
    """
    if not dt:
        return 'Never'
    
    # Convert to user timezone
    if dt.tzinfo is None:
        from datetime import timezone as tz_utc
        dt = dt.replace(tzinfo=tz_utc.utc)
    
    local_dt = dt.astimezone(tz)
    now = datetime.now(tz)
    
    delta = now - local_dt
    
    # Recent times (< 1 day)
    if delta.days == 0:
        hours = delta.seconds // 3600
        minutes = (delta.seconds % 3600) // 60
        
        if hours == 0:
            if minutes == 0:
                return 'Just now'
            if minutes == 1:
                return '1 minute ago'
            return f'{minutes} minutes ago'
        if hours == 1:
            return '1 hour ago'
        return f'{hours} hours ago'
    
    # Recent days (< 7 days)
    if delta.days == 1:
        return 'Yesterday'
    if delta.days < 7:
        return f'{delta.days} days ago'
    
    # Full date for older items
    return local_dt.strftime('%B %d, %Y at %I:%M %p')


class ReportGenerator:
    """Generate reports by filling templates with data from database"""
    
    def __init__(self, database: Database):
        """
        Initialize report generator.
        
        Args:
            database: Database instance
        """
        self.database = database
    
    def generate_report(self, template_html: str, 
                       start_date: Optional[datetime] = None,
                       end_date: Optional[datetime] = None,
                       data_sources: Optional[List[str]] = None,
                       logo_url: str = '/static/img/logo.png',
                       client_id: Optional[str] = None,
                       ai_generator = None) -> str:
        """
        Generate a report from a template.
        
        Args:
            template_html: HTML template with Jinja2 syntax
            start_date: Start date for report data (UTC)
            end_date: End date for report data (UTC)
            data_sources: List of data sources to include
            logo_url: URL/path to logo image
            client_id: Optional client ID to filter data
            ai_generator: Optional AITemplateGenerator instance for exec summary
            
        Returns:
            Rendered HTML report
        """
        # Get user timezone preference
        timezone_str = self.database.get_preference('timezone', 'America/New_York')
        user_tz = pytz.timezone(timezone_str)
        
        # Check for custom logo
        custom_logo = self.database.get_preference('custom_logo_base64')
        if custom_logo:
            logo_url = custom_logo
        
        # Default date range: last 30 days
        if not end_date:
            end_date = datetime.utcnow()
        if not start_date:
            start_date = end_date - timedelta(days=30)
        
        # Calculate all metrics
        context = self._build_context(start_date, end_date, user_tz, data_sources, logo_url, client_id)
        
        # Check if template uses exec_summary and generate it with AI if available
        if ai_generator and ('{{exec_summary}}' in template_html or '{{ exec_summary }}' in template_html):
            try:
                context['exec_summary'] = ai_generator.generate_executive_summary(context)
            except Exception as e:
                # Fallback to default summary if AI generation fails
                import logging
                logging.error(f"AI summary generation failed: {e}")
                context['exec_summary'] = self._generate_summary(context)
        else:
            # Use default summary if no AI or no placeholder
            context['exec_summary'] = context.get('executive_summary', self._generate_summary(context))
        
        # Render template with graceful error handling
        try:
            template = Template(template_html)
            return template.render(**context)
        except Exception as e:
            import logging
            logging.error(f"Template rendering failed: {e}")
            
            # Instead of failing completely, render a debug report
            error_type = type(e).__name__
            error_msg = str(e)
            
            # Extract line number if available
            line_number = None
            if hasattr(e, 'lineno'):
                line_number = e.lineno
            elif 'line' in error_msg.lower():
                # Try to extract line number from error message
                import re
                line_match = re.search(r'line (\d+)', error_msg, re.IGNORECASE)
                if line_match:
                    line_number = int(line_match.group(1))
            
            # Get the problematic line from template if we have a line number
            template_lines = template_html.split('\n')
            error_context = ""
            if line_number and line_number > 0 and line_number <= len(template_lines):
                start_line = max(1, line_number - 2)
                end_line = min(len(template_lines), line_number + 2)
                error_context = "<div style='background: #fff; padding: 15px; border-radius: 4px; margin-top: 10px;'>"
                error_context += "<strong>Template context around the error:</strong><br>"
                error_context += "<pre style='margin: 10px 0; padding: 10px; background: #f8f8f8; border-left: 3px solid #dc2626;'>"
                for i in range(start_line - 1, end_line):
                    line_num = i + 1
                    line_content = template_lines[i].replace('<', '&lt;').replace('>', '&gt;')
                    if line_num == line_number:
                        error_context += f"<span style='color: #dc2626; font-weight: bold;'>→ Line {line_num}: {line_content}</span>\n"
                    else:
                        error_context += f"  Line {line_num}: {line_content}\n"
                error_context += "</pre></div>"
            
            # Provide helpful tips based on error type
            tips = []
            if "undefined" in error_msg.lower():
                tips.append("The template references a variable that doesn't exist")
                tips.append("View all available variables at /report-values")
            if ".days" in error_msg or ".seconds" in error_msg or "timedelta" in error_msg:
                tips.append("Datetime fields are strings, not datetime objects")
                tips.append("Don't use datetime operations like (date1 - date2).days")
            if "strftime" in error_msg:
                tips.append("Can't use .strftime() on string fields")
                tips.append("Datetime fields are already formatted as ISO strings")
            if "selectattr" in error_msg:
                tips.append("Complex selectattr filters may fail")
                tips.append("Use simple loops instead")
            if "len(" in template_html:
                tips.append("Use |length filter instead of len() function")
            
            # Create a helpful debug report
            debug_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Template Error - Debug Report</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            line-height: 1.6;
            color: #333;
            background: #f5f5f5;
            padding: 20px;
        }}
        .error-container {{
            max-width: 900px;
            margin: 0 auto;
            background: #fff;
            border-radius: 8px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            overflow: hidden;
        }}
        .error-header {{
            background: #dc2626;
            color: white;
            padding: 20px 30px;
        }}
        .error-header h1 {{
            font-size: 24px;
            margin-bottom: 8px;
        }}
        .error-header p {{
            opacity: 0.9;
            font-size: 14px;
        }}
        .error-content {{
            padding: 30px;
        }}
        .error-box {{
            background: #fee2e2;
            border-left: 4px solid #dc2626;
            padding: 15px 20px;
            margin: 20px 0;
            border-radius: 4px;
        }}
        .error-box h3 {{
            color: #991b1b;
            font-size: 16px;
            margin-bottom: 10px;
        }}
        .error-box pre {{
            background: #fff;
            padding: 12px;
            border-radius: 4px;
            overflow-x: auto;
            font-size: 13px;
            color: #dc2626;
        }}
        .tips-box {{
            background: #dbeafe;
            border-left: 4px solid #2563eb;
            padding: 15px 20px;
            margin: 20px 0;
            border-radius: 4px;
        }}
        .tips-box h3 {{
            color: #1e40af;
            font-size: 16px;
            margin-bottom: 10px;
        }}
        .tips-box ul {{
            margin-left: 20px;
            color: #1e3a8a;
        }}
        .tips-box li {{
            margin: 8px 0;
        }}
        .help-section {{
            margin: 30px 0;
            padding: 20px;
            background: #f9fafb;
            border-radius: 6px;
        }}
        .help-section h3 {{
            color: #374151;
            margin-bottom: 15px;
        }}
        .help-section ul {{
            margin-left: 20px;
        }}
        .help-section li {{
            margin: 8px 0;
            color: #6b7280;
        }}
        .action-buttons {{
            margin-top: 30px;
            display: flex;
            gap: 15px;
        }}
        .btn {{
            display: inline-block;
            padding: 10px 20px;
            border-radius: 6px;
            text-decoration: none;
            font-weight: 500;
            transition: all 0.2s;
        }}
        .btn-primary {{
            background: #2563eb;
            color: white;
        }}
        .btn-primary:hover {{
            background: #1d4ed8;
        }}
        .btn-secondary {{
            background: #6b7280;
            color: white;
        }}
        .btn-secondary:hover {{
            background: #4b5563;
        }}
        .code {{
            background: #f3f4f6;
            padding: 2px 6px;
            border-radius: 3px;
            font-family: 'Courier New', monospace;
            font-size: 13px;
        }}
    </style>
</head>
<body>
    <div class="error-container">
        <div class="error-header">
            <h1>⚠️ Template Rendering Error</h1>
            <p>Your template encountered an error when trying to generate the report. Don't worry - this helps you fix it!</p>
        </div>
        
        <div class="error-content">
            <div class="error-box">
                <h3>Error Type: {error_type}{f" (Line {line_number})" if line_number else ""}</h3>
                <pre>{error_msg}</pre>
            </div>
            
            {error_context}
            
            {"".join([f'<div class="tips-box"><h3>💡 Quick Fix Tips</h3><ul>' + "".join([f'<li>{tip}</li>' for tip in tips]) + '</ul></div>']) if tips else ''}
            
            <div class="help-section">
                <h3>Common Template Issues & Fixes</h3>
                <ul>
                    <li><strong>Undefined variables:</strong> Check that you're using the correct variable names. Use <span class="code">|default('N/A')</span> or <span class="code">or 'N/A'</span> for optional values.</li>
                    <li><strong>Datetime operations:</strong> Fields like <span class="code">started_at</span> are ISO format strings, not datetime objects. Don't use <span class="code">.days</span> or <span class="code">.strftime()</span> directly.</li>
                    <li><strong>None values:</strong> Always check if a value exists first: <span class="code">{{% if variable %}}{{% endif %}}</span></li>
                    <li><strong>List length:</strong> Use <span class="code">{{{{ items|length }}}}</span> not <span class="code">len(items)</span></li>
                    <li><strong>Loop limits:</strong> Limit loops to avoid huge tables: <span class="code">{{% for item in items[:10] %}}</span></li>
                    <li><strong>Safe defaults:</strong> Use <span class="code">{{{{ value|default('Not Set') }}}}</span> for potentially missing fields</li>
                </ul>
            </div>
            
            <div class="help-section">
                <h3>✅ Safe Template Patterns</h3>
                <ul>
                    <li><span class="code">{{% if device.storage_used_bytes %}}{{{{ (device.storage_used_bytes / 1024**3)|round(1) }}}} GB{{% else %}}N/A{{% endif %}}</span></li>
                    <li><span class="code">{{{{ devices|length }}}} devices found</span></li>
                    <li><span class="code">{{% for backup in backups[:20] %}}...{{% endfor %}}</span> (limit iterations)</li>
                    <li><span class="code">{{{{ agent.display_name or agent.agent_id or 'Unknown' }}}}</span></li>
                    <li>Use <strong>preprocessed variables</strong> like <span class="code">agent_backup_status</span>, <span class="code">device_storage</span> instead of raw arrays when possible!</li>
                </ul>
            </div>
            
            <div class="action-buttons">
                <a href="/templates" class="btn btn-primary">← Back to Templates</a>
                <a href="/report-values" class="btn btn-secondary" target="_blank">View All Variables</a>
            </div>
        </div>
    </div>
</body>
</html>"""
            
            return debug_html
    
    def generate_report_with_base64_images(self, template_html: str,
                                           start_date: Optional[datetime] = None,
                                           end_date: Optional[datetime] = None,
                                           data_sources: Optional[List[str]] = None,
                                           logo_url: str = '/static/img/logo.png',
                                           client_id: Optional[str] = None,
                                           ai_generator = None) -> str:
        """
        Generate a standalone report with all images embedded as base64.
        
        This creates a single HTML file that can be opened anywhere without
        needing access to external image files or URLs.
        
        Args:
            template_html: HTML template with Jinja2 syntax
            start_date: Start date for report data (UTC)
            end_date: End date for report data (UTC)
            data_sources: List of data sources to include
            logo_url: URL/path to logo image
            client_id: Optional client ID to filter data
            ai_generator: Optional AITemplateGenerator instance for exec summary
            
        Returns:
            Rendered HTML report with base64-embedded images
        """
        import re
        import base64
        import os
        
        # Generate report normally first
        html = self.generate_report(
            template_html,
            start_date,
            end_date,
            data_sources,
            logo_url,
            client_id,
            ai_generator
        )
        
        # Find all img tags with src attributes
        img_pattern = re.compile(r'<img([^>]+)src=["\']([^"\']+)["\']([^>]*)>', re.IGNORECASE)
        
        def replace_image(match):
            """Replace image src with base64 data URL"""
            before_src = match.group(1)
            src_url = match.group(2)
            after_src = match.group(3)
            
            try:
                # Determine if local file or remote URL
                if src_url.startswith(('http://', 'https://')):
                    # Remote URL - fetch it
                    try:
                        import requests
                        response = requests.get(src_url, timeout=10)
                        response.raise_for_status()
                        image_data = response.content
                        
                        # Try to determine content type from headers
                        content_type = response.headers.get('content-type', '')
                        if 'image/' in content_type:
                            mime_type = content_type.split(';')[0]
                        else:
                            mime_type = self._get_mime_type_from_url(src_url)
                    except Exception as e:
                        import logging
                        logging.warning(f"Failed to fetch remote image {src_url}: {e}")
                        return match.group(0)  # Return original if fetch fails
                        
                elif src_url.startswith('/'):
                    # Local absolute path - convert to filesystem path
                    # Remove leading slash and resolve relative to workspace
                    workspace_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                    file_path = os.path.join(workspace_path, src_url.lstrip('/'))
                    
                    if not os.path.exists(file_path):
                        import logging
                        logging.warning(f"Image file not found: {file_path}")
                        return match.group(0)  # Return original if file not found
                    
                    with open(file_path, 'rb') as f:
                        image_data = f.read()
                    
                    mime_type = self._get_mime_type_from_url(src_url)
                    
                else:
                    # Relative path or other - skip
                    return match.group(0)
                
                # Convert to base64
                base64_data = base64.b64encode(image_data).decode('utf-8')
                data_url = f'data:{mime_type};base64,{base64_data}'
                
                # Return img tag with data URL
                return f'<img{before_src}src="{data_url}"{after_src}>'
                
            except Exception as e:
                import logging
                logging.error(f"Error converting image {src_url} to base64: {e}")
                return match.group(0)  # Return original on any error
        
        # Replace all images
        html_with_base64 = img_pattern.sub(replace_image, html)
        
        return html_with_base64
    
    @staticmethod
    def _get_mime_type_from_url(url: str) -> str:
        """Determine MIME type from file extension"""
        url_lower = url.lower()
        if url_lower.endswith('.png'):
            return 'image/png'
        if url_lower.endswith(('.jpg', '.jpeg')):
            return 'image/jpeg'
        if url_lower.endswith('.gif'):
            return 'image/gif'
        if url_lower.endswith('.webp'):
            return 'image/webp'
        if url_lower.endswith('.svg'):
            return 'image/svg+xml'
        if url_lower.endswith('.bmp'):
            return 'image/bmp'
        return 'image/png'  # Default fallback
    
    def _build_context(self, start_date: datetime, end_date: datetime,
                      user_tz: pytz.timezone, data_sources: Optional[List[str]],
                      logo_url: str, client_id: Optional[str] = None) -> Dict[str, Any]:
        """Build template context with all calculated metrics"""
        context = {
            'logo_url': logo_url,
            'report_title': 'Slide Backup Report',
            'date_range': f"{self._format_date(start_date, user_tz)} - {self._format_date(end_date, user_tz)}",
            'generated_at': self._format_datetime(datetime.utcnow(), user_tz),
            'timezone': str(user_tz),
            'client_id': client_id,
        }
        
        # Add client name if filtering
        if client_id:
            clients = self.database.get_records('clients', where='client_id = ?', params=(client_id,))
            if clients:
                context['client_name'] = clients[0].get('name', client_id)
                context['report_title'] = f"Slide Backup Report - {context['client_name']}"
        
        # Add data source flags
        if not data_sources:
            data_sources = ['devices', 'agents', 'backups', 'snapshots', 'alerts', 'audits']
        
        context['show_backup_stats'] = 'backups' in data_sources
        context['show_snapshots'] = 'snapshots' in data_sources
        context['show_alerts'] = 'alerts' in data_sources
        context['show_storage'] = 'devices' in data_sources
        context['show_audits'] = 'audits' in data_sources
        context['show_virtualization'] = 'virtual_machines' in data_sources
        
        # Add raw data arrays for advanced template usage
        # These allow templates to access raw database records if needed
        
        # Devices
        if client_id:
            context['devices'] = self.database.get_records('devices', where='client_id = ?', params=(client_id,))
        else:
            context['devices'] = self.database.get_records('devices')
        
        # Agents
        if client_id:
            context['agents'] = self.database.get_records('agents', where='client_id = ?', params=(client_id,))
        else:
            context['agents'] = self.database.get_records('agents')
        
        # Clients (all or just the filtered one)
        if client_id:
            context['clients'] = self.database.get_records('clients', where='client_id = ?', params=(client_id,))
        else:
            context['clients'] = self.database.get_records('clients')
        
        # Backups in date range
        if client_id:
            context['backups'] = self.database.execute_query("""
                SELECT b.* FROM backups b
                JOIN agents a ON b.agent_id = a.agent_id
                WHERE a.client_id = ? AND b.started_at >= ? AND b.started_at <= ?
                ORDER BY b.started_at DESC
            """, (client_id, start_date.isoformat(), end_date.isoformat()))
        else:
            context['backups'] = self.database.execute_query("""
                SELECT * FROM backups 
                WHERE started_at >= ? AND started_at <= ?
                ORDER BY started_at DESC
            """, (start_date.isoformat(), end_date.isoformat()))
        
        # Snapshots in date range
        if client_id:
            context['snapshots'] = self.database.execute_query("""
                SELECT s.* FROM snapshots s
                JOIN agents a ON s.agent_id = a.agent_id
                WHERE a.client_id = ? AND s.backup_started_at >= ? AND s.backup_started_at <= ?
            """, (client_id, start_date.isoformat(), end_date.isoformat()))
        else:
            context['snapshots'] = self.database.execute_query("""
                SELECT * FROM snapshots 
                WHERE backup_started_at >= ? AND backup_started_at <= ?
            """, (start_date.isoformat(), end_date.isoformat()))
        
        # Alerts in date range
        if client_id:
            context['alerts'] = self.database.execute_query("""
                SELECT a.* FROM alerts a
                LEFT JOIN agents ag ON a.agent_id = ag.agent_id
                LEFT JOIN devices d ON a.device_id = d.device_id
                WHERE (ag.client_id = ? OR d.client_id = ?) 
                  AND a.created_at >= ? AND a.created_at <= ?
            """, (client_id, client_id, start_date.isoformat(), end_date.isoformat()))
        else:
            context['alerts'] = self.database.execute_query("""
                SELECT * FROM alerts 
                WHERE created_at >= ? AND created_at <= ?
            """, (start_date.isoformat(), end_date.isoformat()))
        
        # Virtual machines
        if client_id:
            context['virtual_machines'] = self.database.execute_query("""
                SELECT vm.* FROM virtual_machines vm
                JOIN agents a ON vm.agent_id = a.agent_id
                WHERE a.client_id = ?
            """, (client_id,))
        else:
            context['virtual_machines'] = self.database.get_records('virtual_machines')
        
        # Audits in date range
        if client_id:
            context['audits'] = self.database.execute_query("""
                SELECT * FROM audits 
                WHERE client_id = ? AND audit_time >= ? AND audit_time <= ?
                ORDER BY audit_time DESC
                LIMIT 100
            """, (client_id, start_date.isoformat(), end_date.isoformat()))
        else:
            context['audits'] = self.database.execute_query("""
                SELECT * FROM audits 
                WHERE audit_time >= ? AND audit_time <= ?
                ORDER BY audit_time DESC
                LIMIT 100
            """, (start_date.isoformat(), end_date.isoformat()))
        
        # File restores (if any exist)
        if client_id:
            context['file_restores'] = self.database.execute_query("""
                SELECT fr.* FROM file_restores fr
                JOIN agents a ON fr.agent_id = a.agent_id
                WHERE a.client_id = ?
            """, (client_id,))
        else:
            context['file_restores'] = self.database.get_records('file_restores')
        
        # Calculate metrics based on selected data sources
        if 'backups' in data_sources:
            context.update(self._calculate_backup_metrics(start_date, end_date, user_tz, client_id))
        
        if 'snapshots' in data_sources:
            snapshot_metrics = self._calculate_snapshot_metrics(start_date, end_date, client_id)
            context.update(snapshot_metrics)
            # Add latest screenshot
            latest_screenshot = self._get_latest_screenshot(client_id)
            if latest_screenshot:
                context['latest_screenshot'] = latest_screenshot
        
        if 'alerts' in data_sources:
            context.update(self._calculate_alert_metrics(start_date, end_date, client_id))
        
        if 'devices' in data_sources:
            context.update(self._calculate_storage_metrics(client_id))
        
        if 'audits' in data_sources:
            context.update(self._calculate_audit_metrics(start_date, end_date, client_id))
        
        if 'virtual_machines' in data_sources:
            context.update(self._calculate_virtualization_metrics(client_id))
        
        # Add calendar grid data per agent
        context['agent_calendars'] = self._calculate_agent_calendars(start_date, end_date, user_tz, client_id)
        
        # Add snapshot totals by agent
        context['agent_snapshot_totals'] = self._calculate_agent_snapshot_totals(client_id)
        
        # Add screenshot pairs per agent
        context['agent_screenshots'] = self._get_agent_screenshot_pairs(start_date, end_date, user_tz, client_id)
        
        # Add snapshot audit data per agent
        context['agent_snapshot_audit'] = self._prepare_snapshot_audit_data(start_date, end_date, user_tz, client_id)
        
        # Add storage growth metrics
        storage_growth_data = self._calculate_storage_growth(start_date, end_date, client_id)
        context.update(storage_growth_data)
        
        # Add agent configuration overview metrics
        config_metrics = self._calculate_agent_config_metrics(user_tz, client_id)
        context.update(config_metrics)
        
        # Generate executive summary
        context['executive_summary'] = self._generate_summary(context)
        
        return context
    
    def _parse_datetime(self, date_str: str) -> datetime:
        """
        Safely parse datetime strings from database.
        Handles various formats including non-standard microseconds.
        """
        if not date_str:
            return None
        
        try:
            # Remove 'Z' and replace with +00:00 for UTC
            date_str = date_str.replace('Z', '+00:00')
            return datetime.fromisoformat(date_str)
        except ValueError:
            # Handle malformed microseconds (e.g., .00181 instead of .001810)
            # Try parsing without timezone first, then add UTC
            try:
                if '+' in date_str:
                    date_part = date_str.split('+')[0]
                else:
                    date_part = date_str
                
                # Parse up to seconds
                if '.' in date_part:
                    main_part, micro_part = date_part.rsplit('.', 1)
                    # Pad or truncate microseconds to 6 digits
                    micro_part = micro_part.ljust(6, '0')[:6]
                    date_str = f"{main_part}.{micro_part}+00:00"
                
                return datetime.fromisoformat(date_str)
            except Exception:
                # Last resort: try without microseconds
                if '.' in date_str:
                    date_str = date_str.split('.')[0] + '+00:00'
                return datetime.fromisoformat(date_str)
    
    def _calculate_backup_metrics(self, start_date: datetime, end_date: datetime,
                                  user_tz: pytz.timezone, client_id: Optional[str] = None) -> Dict[str, Any]:
        """Calculate backup-related metrics"""
        # Build query with optional client filter
        if client_id:
            backups = self.database.execute_query("""
                SELECT b.* FROM backups b
                JOIN agents a ON b.agent_id = a.agent_id
                WHERE a.client_id = ? AND b.started_at >= ? AND b.started_at <= ?
                ORDER BY b.started_at DESC
            """, (client_id, start_date.isoformat(), end_date.isoformat()))
        else:
            backups = self.database.execute_query("""
                SELECT * FROM backups 
                WHERE started_at >= ? AND started_at <= ?
                ORDER BY started_at DESC
            """, (start_date.isoformat(), end_date.isoformat()))
        
        total_backups = len(backups)
        successful_backups = sum(1 for b in backups if b['status'] == 'succeeded')
        failed_backups = sum(1 for b in backups if b['status'] == 'failed')
        success_rate = round(successful_backups / total_backups * 100, 1) if total_backups > 0 else 0
        
        # Get agent backup status
        if client_id:
            agents = self.database.get_records('agents', where='client_id = ?', params=(client_id,))
        else:
            agents = self.database.get_records('agents')
        agent_backup_status = []
        
        for agent in agents:
            agent_backups = [b for b in backups if b['agent_id'] == agent['agent_id']]
            if agent_backups:
                last_backup = agent_backups[0]
                duration = ''
                if last_backup.get('ended_at') and last_backup.get('started_at'):
                    start = self._parse_datetime(last_backup['started_at'])
                    end = self._parse_datetime(last_backup['ended_at'])
                    if start and end:
                        delta = end - start
                        duration = self._format_duration(delta)
                
                status = last_backup['status']
                status_class = 'success' if status == 'succeeded' else 'danger' if status == 'failed' else 'warning'
                
                last_backup_dt = self._parse_datetime(last_backup['started_at'])
                
                agent_backup_status.append({
                    'name': agent['display_name'] or agent['hostname'],
                    'last_backup': self._format_datetime(last_backup_dt, user_tz) if last_backup_dt else 'Unknown',
                    'status': status.title(),
                    'status_class': status_class,
                    'duration': duration
                })
        
        return {
            'total_backups': total_backups,
            'successful_backups': successful_backups,
            'failed_backups': failed_backups,
            'success_rate': success_rate,
            'agent_backup_status': agent_backup_status
        }
    
    def _calculate_snapshot_metrics(self, start_date: datetime, end_date: datetime, 
                                    client_id: Optional[str] = None) -> Dict[str, Any]:
        """Calculate snapshot-related metrics within date range"""
        # Get snapshots in date range based on backup_started_at
        if client_id:
            snapshots = self.database.execute_query("""
                SELECT s.* FROM snapshots s
                JOIN agents a ON s.agent_id = a.agent_id
                WHERE a.client_id = ? AND s.backup_started_at >= ? AND s.backup_started_at <= ?
            """, (client_id, start_date.isoformat(), end_date.isoformat()))
        else:
            snapshots = self.database.execute_query("""
                SELECT * FROM snapshots 
                WHERE backup_started_at >= ? AND backup_started_at <= ?
            """, (start_date.isoformat(), end_date.isoformat()))
        
        # Count active snapshots (those not deleted)
        active_snapshots = sum(1 for s in snapshots if not s.get('exists_deleted'))
        
        # Count by location for active snapshots - parse from locations JSON field
        local_count = 0
        cloud_count = 0
        
        for s in snapshots:
            if not s.get('exists_deleted'):  # Only count active snapshots
                locations_json = s.get('locations', '')
                if locations_json:
                    try:
                        import json
                        locations = json.loads(locations_json)
                        if isinstance(locations, list):
                            for loc in locations:
                                if loc.get('type') == 'local':
                                    local_count += 1
                                elif loc.get('type') == 'cloud':
                                    cloud_count += 1
                    except Exception:
                        # Fallback to exists_local/exists_cloud if parsing fails
                        if s.get('exists_local'):
                            local_count += 1
                        if s.get('exists_cloud'):
                            cloud_count += 1
        
        # Count deletion types using proper database fields
        retention_deleted = sum(1 for s in snapshots if s.get('exists_deleted_retention'))
        manually_deleted = sum(1 for s in snapshots if s.get('exists_deleted_manual'))
        other_deleted = sum(1 for s in snapshots if s.get('exists_deleted_other'))
        
        # Total deleted snapshots
        deleted_snapshots = retention_deleted + manually_deleted + other_deleted
        
        return {
            'active_snapshots': active_snapshots,
            'deleted_snapshots': deleted_snapshots,
            'local_snapshots': local_count,
            'cloud_snapshots': cloud_count,
            'retention_deleted_count': retention_deleted,
            'manually_deleted_count': manually_deleted,
            'other_deleted_count': other_deleted
        }
    
    def _calculate_alert_metrics(self, start_date: datetime, end_date: datetime,
                                 client_id: Optional[str] = None) -> Dict[str, Any]:
        """Calculate alert-related metrics within date range"""
        # Get alerts created in date range
        if client_id:
            alerts = self.database.execute_query("""
                SELECT a.* FROM alerts a
                LEFT JOIN agents ag ON a.agent_id = ag.agent_id
                LEFT JOIN devices d ON a.device_id = d.device_id
                WHERE (ag.client_id = ? OR d.client_id = ?) 
                  AND a.created_at >= ? AND a.created_at <= ?
            """, (client_id, client_id, start_date.isoformat(), end_date.isoformat()))
        else:
            alerts = self.database.execute_query("""
                SELECT * FROM alerts 
                WHERE created_at >= ? AND created_at <= ?
            """, (start_date.isoformat(), end_date.isoformat()))
        
        total_alerts = len(alerts)
        unresolved_alerts = sum(1 for a in alerts if not a.get('resolved'))
        resolved_alerts = sum(1 for a in alerts if a.get('resolved'))
        
        return {
            'total_alerts': total_alerts,
            'unresolved_alerts': unresolved_alerts,
            'resolved_alerts': resolved_alerts
        }
    
    def _calculate_storage_metrics(self, client_id: Optional[str] = None) -> Dict[str, Any]:
        """Calculate storage-related metrics"""
        if client_id:
            devices = self.database.get_records('devices', where='client_id = ?', params=(client_id,))
        else:
            devices = self.database.get_records('devices')
        
        device_storage = []
        for device in devices:
            used = device.get('storage_used_bytes') or 0
            total = device.get('storage_total_bytes') or 0
            
            if total and total > 0:
                percent = round(used / total * 100, 1)
                device_storage.append({
                    'name': device.get('display_name') or device.get('hostname') or 'Unknown',
                    'used': self._format_bytes(used),
                    'total': self._format_bytes(total),
                    'percent': percent
                })
        
        return {
            'device_storage': device_storage
        }
    
    def _calculate_audit_metrics(self, start_date: datetime, end_date: datetime,
                                 client_id: Optional[str] = None) -> Dict[str, Any]:
        """Calculate audit log metrics"""
        if client_id:
            audits = self.database.execute_query("""
                SELECT * FROM audits 
                WHERE client_id = ? AND audit_time >= ? AND audit_time <= ?
                ORDER BY audit_time DESC
                LIMIT 100
            """, (client_id, start_date.isoformat(), end_date.isoformat()))
        else:
            audits = self.database.execute_query("""
                SELECT * FROM audits 
                WHERE audit_time >= ? AND audit_time <= ?
                ORDER BY audit_time DESC
                LIMIT 100
            """, (start_date.isoformat(), end_date.isoformat()))
        
        total_audits = len(audits)
        
        # Count by action type
        action_counts = {}
        for audit in audits:
            action = audit['action']
            action_counts[action] = action_counts.get(action, 0) + 1
        
        return {
            'total_audits': total_audits,
            'audit_actions': action_counts,
            'recent_audits': audits[:20]  # Top 20 most recent
        }
    
    def _calculate_virtualization_metrics(self, client_id: Optional[str] = None) -> Dict[str, Any]:
        """Calculate virtualization metrics"""
        if client_id:
            # VMs are linked via agents
            vms = self.database.execute_query("""
                SELECT vm.* FROM virtual_machines vm
                JOIN agents a ON vm.agent_id = a.agent_id
                WHERE a.client_id = ?
            """, (client_id,))
        else:
            vms = self.database.get_records('virtual_machines')
        
        total_vms = len(vms)
        running_vms = sum(1 for vm in vms if vm['state'] == 'running')
        stopped_vms = sum(1 for vm in vms if vm['state'] == 'stopped')
        
        return {
            'total_vms': total_vms,
            'running_vms': running_vms,
            'stopped_vms': stopped_vms
        }
    
    def _generate_summary(self, context: Dict[str, Any]) -> str:
        """Generate executive summary text - concise narrative for auditors"""
        parts = []
        
        if context.get('show_backup_stats'):
            parts.append(
                f"During this reporting period, {context['total_backups']} backups were executed "
                f"achieving a {context['success_rate']}% success rate"
            )
        
        if context.get('show_snapshots'):
            parts.append(
                f"with {context['active_snapshots']} active snapshots maintained across "
                f"local and cloud storage locations"
            )
        
        if context.get('show_alerts'):
            if context['unresolved_alerts'] > 0:
                parts.append(
                    f"There are {context['unresolved_alerts']} unresolved alerts requiring attention"
                )
            else:
                parts.append(f"All alerts have been resolved")
        
        if parts:
            summary = '. '.join(parts) + '.'
            return summary.replace('..', '.')
        return 'No data available for the selected reporting period.'
    
    @staticmethod
    def _format_date(dt: datetime, tz: pytz.timezone) -> str:
        """Format date for display"""
        return dt.astimezone(tz).strftime('%Y-%m-%d')
    
    @staticmethod
    def _format_datetime(dt: datetime, tz: pytz.timezone) -> str:
        """Format datetime for display"""
        return dt.astimezone(tz).strftime('%Y-%m-%d %H:%M:%S %Z')
    
    @staticmethod
    def _format_duration(delta: timedelta) -> str:
        """Format duration for display"""
        seconds = int(delta.total_seconds())
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        secs = seconds % 60
        
        if hours > 0:
            return f"{hours}h {minutes}m"
        if minutes > 0:
            return f"{minutes}m"
        return f"{secs}s"
    
    def _get_latest_screenshot(self, client_id: Optional[str] = None) -> Optional[Dict[str, str]]:
        """Get the latest screenshot from snapshots"""
        try:
            if client_id:
                snapshots = self.database.execute_query("""
                    SELECT s.*, a.display_name as agent_name, a.hostname
                    FROM snapshots s
                    JOIN agents a ON s.agent_id = a.agent_id
                    WHERE a.client_id = ? 
                      AND s.verify_boot_screenshot_url IS NOT NULL 
                      AND s.verify_boot_screenshot_url != ''
                    ORDER BY s.backup_started_at DESC
                    LIMIT 1
                """, (client_id,))
            else:
                snapshots = self.database.execute_query("""
                    SELECT s.*, a.display_name as agent_name, a.hostname
                    FROM snapshots s
                    LEFT JOIN agents a ON s.agent_id = a.agent_id
                    WHERE s.verify_boot_screenshot_url IS NOT NULL 
                      AND s.verify_boot_screenshot_url != ''
                    ORDER BY s.backup_started_at DESC
                    LIMIT 1
                """)
            
            if snapshots:
                snapshot = snapshots[0]
                agent_name = snapshot.get('agent_name') or snapshot.get('hostname') or 'Unknown'
                
                # Get user timezone for formatting
                timezone_str = self.database.get_preference('timezone', 'America/New_York')
                user_tz = pytz.timezone(timezone_str)
                
                captured_at = 'Unknown'
                if snapshot.get('backup_started_at'):
                    try:
                        dt = self._parse_datetime(snapshot['backup_started_at'])
                        captured_at = self._format_datetime(dt, user_tz)
                    except Exception:
                        pass
                
                return {
                    'url': snapshot['verify_boot_screenshot_url'],
                    'agent_name': agent_name,
                    'captured_at': captured_at
                }
        except Exception as e:
            import logging
            logging.error(f"Error fetching latest screenshot: {e}")
        
        return None
    
    def _calculate_agent_calendars(self, start_date: datetime, end_date: datetime,
                                   user_tz: pytz.timezone, client_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Generate calendar grid data per agent showing daily backup/retention status"""
        from datetime import timezone as tz_utc
        
        # Get all agents
        if client_id:
            agents = self.database.get_records('agents', where='client_id = ?', params=(client_id,))
        else:
            agents = self.database.get_records('agents')
        
        agent_calendars = []
        
        for agent in agents:
            agent_id = agent['agent_id']
            agent_name = agent.get('display_name') or agent.get('hostname') or 'Unknown'
            
            # Get backups for this agent in the date range
            backups = self.database.execute_query("""
                SELECT * FROM backups 
                WHERE agent_id = ? AND started_at >= ? AND started_at <= ?
                ORDER BY started_at
            """, (agent_id, start_date.isoformat(), end_date.isoformat()))
            
            # Get snapshots for this agent in the date range
            snapshots = self.database.execute_query("""
                SELECT * FROM snapshots 
                WHERE agent_id = ? AND backup_started_at >= ? AND backup_started_at <= ?
            """, (agent_id, start_date.isoformat(), end_date.isoformat()))
            
            # Build calendar grid
            calendar_grid = []
            # Ensure dates are timezone-aware for comparison
            if start_date.tzinfo is None:
                start_date = start_date.replace(tzinfo=tz_utc.utc)
            if end_date.tzinfo is None:
                end_date = end_date.replace(tzinfo=tz_utc.utc)
            
            current_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
            end_date_normalized = end_date.replace(hour=23, minute=59, second=59, microsecond=999999)
            
            while current_date <= end_date_normalized:
                next_date = current_date + timedelta(days=1)
                
                # Find backups on this day
                day_backups = []
                for backup in backups:
                    backup_dt = self._parse_datetime(backup['started_at'])
                    if backup_dt:
                        if backup_dt.tzinfo is None:
                            backup_dt = backup_dt.replace(tzinfo=tz_utc.utc)
                        if current_date <= backup_dt < next_date:
                            day_backups.append(backup)
                
                # Count backup completion
                total_backups = len(day_backups)
                successful_backups = sum(1 for b in day_backups if b['status'] == 'succeeded')
                failed_backups = sum(1 for b in day_backups if b['status'] == 'failed')
                missing_backups = total_backups - successful_backups if total_backups > 0 else 0
                
                # Determine backup status for the day
                backup_status = 'none'
                if day_backups:
                    if successful_backups == total_backups:
                        backup_status = 'success'
                    elif failed_backups > 0:
                        backup_status = 'failed'
                    else:
                        backup_status = 'running'
                
                # Determine color coding based on missing backups
                completion_color = 'none'
                if total_backups > 0:
                    if missing_backups == 0:
                        completion_color = 'green'
                    elif missing_backups == 1:
                        completion_color = 'yellow'
                    else:
                        completion_color = 'red'
                
                # Count all snapshots CREATED on this day (including those later deleted)
                snapshots_created_count = sum(
                    1 for s in snapshots
                    if self._parse_datetime(s.get('backup_started_at'))
                    and current_date <= self._parse_datetime(s.get('backup_started_at')) < next_date
                )
                
                # Count snapshots REMAINING from this day (not deleted by retention)
                snapshots_remaining_count = sum(
                    1 for s in snapshots
                    if self._parse_datetime(s.get('backup_started_at'))
                    and current_date <= self._parse_datetime(s.get('backup_started_at')) < next_date
                    and not s.get('deleted')  # Only count snapshots that still exist (not deleted)
                )
                
                # Track snapshot locations
                local_only = 0
                cloud_only = 0
                both_locations = 0
                
                # Get snapshots from this day
                day_snapshots = [
                    s for s in snapshots
                    if self._parse_datetime(s.get('backup_started_at'))
                    and current_date <= self._parse_datetime(s.get('backup_started_at')) < next_date
                ]
                
                # Count local and cloud snapshots separately
                local_snapshots_count = 0
                cloud_snapshots_count = 0
                
                for s in day_snapshots:
                    # Parse locations from JSON field
                    has_local = False
                    has_cloud = False
                    
                    locations_json = s.get('locations', '')
                    if locations_json:
                        try:
                            import json
                            locations = json.loads(locations_json)
                            if isinstance(locations, list):
                                for loc in locations:
                                    if loc.get('type') == 'local':
                                        has_local = True
                                    elif loc.get('type') == 'cloud':
                                        has_cloud = True
                        except Exception:
                            # Fallback to exists_local/exists_cloud if parsing fails
                            has_local = s.get('exists_local', 0)
                            has_cloud = s.get('exists_cloud', 0)
                    
                    if has_local:
                        local_snapshots_count += 1
                    if has_cloud:
                        cloud_snapshots_count += 1
                    
                    if has_local and has_cloud:
                        both_locations += 1
                    elif has_local:
                        local_only += 1
                    elif has_cloud:
                        cloud_only += 1
                
                # Determine location display string
                if both_locations > 0:
                    snapshot_location_display = 'LC'
                elif local_only > 0 and cloud_only > 0:
                    snapshot_location_display = 'LC'
                elif local_only > 0:
                    snapshot_location_display = 'L'
                elif cloud_only > 0:
                    snapshot_location_display = 'C'
                else:
                    snapshot_location_display = ''
                
                # Check if there's a snapshot from this day
                has_snapshot = bool(day_snapshots)
                
                calendar_grid.append({
                    'date': current_date.strftime('%Y-%m-%d'),
                    'day_of_week': current_date.strftime('%a'),
                    'day_number': current_date.day,
                    'backup_status': backup_status,
                    'snapshots_created': snapshots_created_count,  # Total snapshots created this day
                    'snapshots_remaining': snapshots_remaining_count,  # Snapshots still retained (not deleted)
                    'local_snapshots': local_snapshots_count,  # Count of local snapshots
                    'cloud_snapshots': cloud_snapshots_count,  # Count of cloud snapshots
                    'has_snapshot': has_snapshot,
                    'total_backups': total_backups,
                    'successful_backups': successful_backups,
                    'failed_backups': failed_backups,
                    'completion_ratio': f'{successful_backups}/{total_backups}' if total_backups > 0 else '-',
                    'completion_color': completion_color,
                    'snapshot_location_local': local_only,
                    'snapshot_location_cloud': cloud_only,
                    'snapshot_location_both': both_locations,
                    'snapshot_location_display': snapshot_location_display
                })
                
                current_date = next_date
            
            # Reorder calendar grid to start weeks on Sunday
            if calendar_grid:
                # Python's weekday(): 0=Monday, 6=Sunday
                first_day = datetime.fromisoformat(calendar_grid[0]['date'])
                first_weekday = first_day.weekday()
                
                # Calculate how many empty days to prepend
                # If Monday (0), need 1 empty day; if Tuesday (1), need 2, etc.
                # If Sunday (6), need 0 empty days
                if first_weekday == 6:
                    days_to_prepend = 0
                else:
                    days_to_prepend = first_weekday + 1
                
                # Prepend empty placeholder days
                empty_days = []
                for i in range(days_to_prepend):
                    empty_days.append({
                        'date': '',
                        'day_of_week': '',
                        'day_number': '',
                        'backup_status': 'none',
                        'snapshots_created': 0,
                        'snapshots_remaining': 0,
                        'local_snapshots': 0,
                        'cloud_snapshots': 0,
                        'has_snapshot': False,
                        'total_backups': 0,
                        'successful_backups': 0,
                        'failed_backups': 0,
                        'completion_ratio': '-',
                        'completion_color': 'none',
                        'snapshot_location_local': 0,
                        'snapshot_location_cloud': 0,
                        'snapshot_location_both': 0,
                        'snapshot_location_display': ''
                    })
                
                calendar_grid = empty_days + calendar_grid
                
                # Update day_of_week labels to ensure Sunday is first
                day_names = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']
                for i, day in enumerate(calendar_grid):
                    if day['date']:  # Only update non-empty days
                        day_date = datetime.fromisoformat(day['date'])
                        # Python weekday: 0=Mon, 6=Sun -> map to our day_names where 0=Sun
                        weekday_index = (day_date.weekday() + 1) % 7
                        day['day_of_week'] = day_names[weekday_index]
            
            agent_calendars.append({
                'agent_name': agent_name,
                'agent_id': agent_id,
                'calendar_grid': calendar_grid
            })
        
        return agent_calendars
    
    def _get_agent_screenshot_pairs(self, start_date: datetime, end_date: datetime,
                                    user_tz: pytz.timezone, client_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Fetch oldest and newest screenshots per agent within reporting period"""
        # Get all agents
        if client_id:
            agents = self.database.get_records('agents', where='client_id = ?', params=(client_id,))
        else:
            agents = self.database.get_records('agents')
        
        agent_screenshots = []
        
        for agent in agents:
            agent_id = agent['agent_id']
            agent_name = agent.get('display_name') or agent.get('hostname') or 'Unknown'
            
            # Get oldest screenshot in range
            if client_id:
                oldest_snapshots = self.database.execute_query("""
                    SELECT s.* FROM snapshots s
                    JOIN agents a ON s.agent_id = a.agent_id
                    WHERE a.client_id = ? AND s.agent_id = ?
                      AND s.backup_started_at >= ? AND s.backup_started_at <= ?
                      AND s.verify_boot_screenshot_url IS NOT NULL 
                      AND s.verify_boot_screenshot_url != ''
                    ORDER BY s.backup_started_at ASC
                    LIMIT 1
                """, (client_id, agent_id, start_date.isoformat(), end_date.isoformat()))
            else:
                oldest_snapshots = self.database.execute_query("""
                    SELECT * FROM snapshots 
                    WHERE agent_id = ?
                      AND backup_started_at >= ? AND backup_started_at <= ?
                      AND verify_boot_screenshot_url IS NOT NULL 
                      AND verify_boot_screenshot_url != ''
                    ORDER BY backup_started_at ASC
                    LIMIT 1
                """, (agent_id, start_date.isoformat(), end_date.isoformat()))
            
            # Get newest screenshot in range
            if client_id:
                newest_snapshots = self.database.execute_query("""
                    SELECT s.* FROM snapshots s
                    JOIN agents a ON s.agent_id = a.agent_id
                    WHERE a.client_id = ? AND s.agent_id = ?
                      AND s.backup_started_at >= ? AND s.backup_started_at <= ?
                      AND s.verify_boot_screenshot_url IS NOT NULL 
                      AND s.verify_boot_screenshot_url != ''
                    ORDER BY s.backup_started_at DESC
                    LIMIT 1
                """, (client_id, agent_id, start_date.isoformat(), end_date.isoformat()))
            else:
                newest_snapshots = self.database.execute_query("""
                    SELECT * FROM snapshots 
                    WHERE agent_id = ?
                      AND backup_started_at >= ? AND backup_started_at <= ?
                      AND verify_boot_screenshot_url IS NOT NULL 
                      AND verify_boot_screenshot_url != ''
                    ORDER BY backup_started_at DESC
                    LIMIT 1
                """, (agent_id, start_date.isoformat(), end_date.isoformat()))
            
            oldest_screenshot = None
            newest_screenshot = None
            
            if oldest_snapshots:
                snapshot = oldest_snapshots[0]
                oldest_screenshot = {
                    'url': snapshot['verify_boot_screenshot_url'],
                    'date': self._format_datetime(self._parse_datetime(snapshot['backup_started_at']), user_tz),
                    'snapshot_id': snapshot['snapshot_id'][:12]
                }
            
            if newest_snapshots:
                snapshot = newest_snapshots[0]
                newest_screenshot = {
                    'url': snapshot['verify_boot_screenshot_url'],
                    'date': self._format_datetime(self._parse_datetime(snapshot['backup_started_at']), user_tz),
                    'snapshot_id': snapshot['snapshot_id'][:12]
                }
            
            # Only include agents that have at least one screenshot
            if oldest_screenshot or newest_screenshot:
                agent_screenshots.append({
                    'agent_name': agent_name,
                    'agent_id': agent_id,
                    'oldest_screenshot': oldest_screenshot,
                    'newest_screenshot': newest_screenshot
                })
        
        return agent_screenshots
    
    def _prepare_snapshot_audit_data(self, start_date: datetime, end_date: datetime,
                                      user_tz: pytz.timezone, client_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Prepare snapshot audit data grouped by agent.
        
        Returns list of agents with their snapshots, including:
        - date_formatted: Snapshot date/time in user timezone
        - location_local: Boolean if exists locally
        - location_cloud: Boolean if exists in cloud
        - verify_boot_passed: Boolean if screenshot verification passed
        - verify_fs_passed: Boolean if filesystem verification passed
        - screenshot_url: URL to verification screenshot
        """
        # Get all agents
        if client_id:
            agents = self.database.get_records('agents', where='client_id = ?', params=(client_id,))
        else:
            agents = self.database.get_records('agents')
        
        agent_audit_data = []
        
        for agent in agents:
            agent_id = agent['agent_id']
            agent_name = agent.get('display_name') or agent.get('hostname') or agent_id
            
            # Get all snapshots for this agent in the date range
            if client_id:
                snapshots = self.database.execute_query("""
                    SELECT s.* FROM snapshots s
                    JOIN agents a ON s.agent_id = a.agent_id
                    WHERE a.client_id = ? AND s.agent_id = ?
                      AND s.backup_started_at >= ? AND s.backup_started_at <= ?
                    ORDER BY s.backup_started_at DESC
                """, (client_id, agent_id, start_date.isoformat(), end_date.isoformat()))
            else:
                snapshots = self.database.execute_query("""
                    SELECT * FROM snapshots 
                    WHERE agent_id = ?
                      AND backup_started_at >= ? AND backup_started_at <= ?
                    ORDER BY backup_started_at DESC
                """, (agent_id, start_date.isoformat(), end_date.isoformat()))
            
            # Process each snapshot
            snapshot_list = []
            for snapshot in snapshots:
                snapshot_dt = self._parse_datetime(snapshot.get('backup_started_at'))
                
                # Parse locations from JSON field (same logic as calendar grid)
                has_local = False
                has_cloud = False
                
                locations_json = snapshot.get('locations', '')
                if locations_json:
                    try:
                        import json
                        locations = json.loads(locations_json)
                        if isinstance(locations, list):
                            for loc in locations:
                                if loc.get('type') == 'local':
                                    has_local = True
                                elif loc.get('type') == 'cloud':
                                    has_cloud = True
                    except Exception:
                        # Fallback to exists_local/exists_cloud if parsing fails
                        has_local = bool(snapshot.get('exists_local', 0))
                        has_cloud = bool(snapshot.get('exists_cloud', 0))
                
                # Only include snapshots that exist in at least one location
                if has_local or has_cloud:
                    snapshot_data = {
                        'date_formatted': self._format_datetime(snapshot_dt, user_tz) if snapshot_dt else 'Unknown',
                        'location_local': has_local,
                        'location_cloud': has_cloud,
                        'verify_boot_passed': snapshot.get('verify_boot_status') == 'success',
                        'verify_fs_passed': snapshot.get('verify_fs_status') == 'success',
                        'screenshot_url': snapshot.get('verify_boot_screenshot_url') if snapshot.get('verify_boot_screenshot_url') else None
                    }
                    snapshot_list.append(snapshot_data)
            
            # Only include agents that have snapshots in the date range
            if snapshot_list:
                agent_audit_data.append({
                    'agent_name': agent_name,
                    'agent_id': agent_id,
                    'snapshots': snapshot_list
                })
        
        return agent_audit_data
    
    def _calculate_agent_snapshot_totals(self, client_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Calculate total local and cloud snapshot counts per agent.
        
        Returns list of dicts with agent_name, local_count, cloud_count
        """
        # Get all agents
        if client_id:
            agents = self.database.get_records('agents', where='client_id = ?', params=(client_id,))
        else:
            agents = self.database.get_records('agents')
        
        agent_totals = []
        
        for agent in agents:
            agent_id = agent['agent_id']
            agent_name = agent.get('display_name') or agent.get('hostname') or 'Unknown'
            
            # Get all snapshots for this agent (not deleted)
            # Use exists_deleted field which is 0 for active snapshots, 1 for deleted
            snapshots = self.database.execute_query("""
                SELECT * FROM snapshots 
                WHERE agent_id = ? AND (exists_deleted IS NULL OR exists_deleted = 0)
            """, (agent_id,))
            
            # Count by location - parse from locations JSON field
            local_count = 0
            cloud_count = 0
            
            for s in snapshots:
                locations_json = s.get('locations', '')
                if locations_json:
                    try:
                        import json
                        locations = json.loads(locations_json)
                        if isinstance(locations, list):
                            for loc in locations:
                                if loc.get('type') == 'local':
                                    local_count += 1
                                elif loc.get('type') == 'cloud':
                                    cloud_count += 1
                    except Exception:
                        # Fallback to exists_local/exists_cloud if parsing fails
                        if s.get('exists_local'):
                            local_count += 1
                        if s.get('exists_cloud'):
                            cloud_count += 1
            
            agent_totals.append({
                'agent_name': agent_name,
                'local_count': local_count,
                'cloud_count': cloud_count
            })
        
        return agent_totals
    
    def _calculate_storage_growth(self, start_date: datetime, end_date: datetime,
                                  client_id: Optional[str] = None) -> Dict[str, Any]:
        """Calculate overall and per-device storage growth between start and end dates"""
        # Get devices
        if client_id:
            devices = self.database.get_records('devices', where='client_id = ?', params=(client_id,))
        else:
            devices = self.database.get_records('devices')
        
        # For simplicity, we'll use current storage values as "end" and estimate "start"
        # In a real system, you'd want historical storage snapshots
        # This is a limitation of the current data model
        
        overall_start_bytes = 0
        overall_end_bytes = 0
        device_growth_list = []
        
        for device in devices:
            device_name = device.get('display_name') or device.get('hostname') or 'Unknown'
            storage_used = device.get('storage_used_bytes') or 0
            storage_total = device.get('storage_total_bytes') or 0
            
            # Get backups for this device to estimate growth
            device_id = device['device_id']
            
            # Get agents for this device
            agents_on_device = self.database.get_records('agents', where='device_id = ?', params=(device_id,))
            
            # Estimate start storage by looking at backup data sizes
            # This is approximate - ideally we'd have historical storage data
            start_storage = storage_used
            
            for agent in agents_on_device:
                # Get backups in date range for this agent
                backups = self.database.execute_query("""
                    SELECT * FROM backups 
                    WHERE agent_id = ? AND started_at >= ? AND started_at <= ?
                    ORDER BY started_at
                """, (agent['agent_id'], start_date.isoformat(), end_date.isoformat()))
                
                # Rough estimate: assume linear growth based on backup count
                # In reality, this would need actual storage metrics over time
                if backups and storage_used > 0:
                    start_storage = int(storage_used * 0.85)  # Assume 15% growth as estimate
            
            growth_bytes = storage_used - start_storage
            growth_percent = 0
            if start_storage > 0:
                growth_percent = round((growth_bytes / start_storage) * 100, 1)
            
            overall_start_bytes += start_storage
            overall_end_bytes += storage_used
            
            device_growth_list.append({
                'device_name': device_name,
                'start_bytes': start_storage,
                'end_bytes': storage_used,
                'start_formatted': self._format_bytes(start_storage),
                'end_formatted': self._format_bytes(storage_used),
                'growth_bytes': growth_bytes,
                'growth_formatted': self._format_bytes(abs(growth_bytes)),
                'growth_percent': growth_percent,
                'is_growth': growth_bytes >= 0
            })
        
        overall_growth = overall_end_bytes - overall_start_bytes
        overall_growth_percent = 0
        if overall_start_bytes > 0:
            overall_growth_percent = round((overall_growth / overall_start_bytes) * 100, 1)
        
        return {
            'storage_growth': {
                'start_bytes': overall_start_bytes,
                'end_bytes': overall_end_bytes,
                'start_formatted': self._format_bytes(overall_start_bytes),
                'end_formatted': self._format_bytes(overall_end_bytes),
                'growth_bytes': overall_growth,
                'growth_formatted': self._format_bytes(abs(overall_growth)),
                'growth_percent': overall_growth_percent,
                'is_growth': overall_growth >= 0
            },
            'device_storage_growth': device_growth_list
        }
    
    def _calculate_agent_config_metrics(self, user_tz: pytz.timezone, 
                                        client_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Calculate agent configuration overview with outlier detection.
        
        Returns structured data showing devices with their agents, including:
        - Full configuration details
        - Last successful backup date and duration
        - Outlier flags (slow backup, old backup, config differences)
        """
        from collections import Counter
        
        # Get all devices
        if client_id:
            devices = self.database.get_records('devices', where='client_id = ?', params=(client_id,))
        else:
            devices = self.database.get_records('devices')
        
        # Get all agents
        if client_id:
            all_agents = self.database.get_records('agents', where='client_id = ?', params=(client_id,))
        else:
            all_agents = self.database.get_records('agents')
        
        # Collect configuration stats for outlier detection
        os_versions = []
        encryption_algorithms = []
        agent_versions = []
        platforms = []
        
        for agent in all_agents:
            if agent.get('os') and agent.get('os_version'):
                os_versions.append(f"{agent['os']} {agent['os_version']}")
            if agent.get('encryption_algorithm'):
                encryption_algorithms.append(agent['encryption_algorithm'])
            if agent.get('agent_version'):
                agent_versions.append(agent['agent_version'])
            if agent.get('platform'):
                platforms.append(agent['platform'])
        
        # Find most common values
        most_common_os = Counter(os_versions).most_common(1)[0][0] if os_versions else None
        most_common_encryption = Counter(encryption_algorithms).most_common(1)[0][0] if encryption_algorithms else None
        most_common_agent_version = Counter(agent_versions).most_common(1)[0][0] if agent_versions else None
        most_common_platform = Counter(platforms).most_common(1)[0][0] if platforms else None
        
        device_list = []
        total_agents = 0
        slow_backup_count = 0
        old_backup_count = 0
        config_outlier_count = 0
        
        for device in devices:
            device_id = device['device_id']
            
            # Get agents for this device
            if client_id:
                device_agents = self.database.get_records('agents', 
                    where='device_id = ? AND client_id = ?', 
                    params=(device_id, client_id))
            else:
                device_agents = self.database.get_records('agents', 
                    where='device_id = ?', 
                    params=(device_id,))
            
            agent_list = []
            
            for agent in device_agents:
                agent_id = agent['agent_id']
                total_agents += 1
                
                # Get last successful backup for this agent
                last_successful_backup = self.database.execute_query("""
                    SELECT * FROM backups 
                    WHERE agent_id = ? AND status = 'succeeded'
                    ORDER BY started_at DESC
                    LIMIT 1
                """, (agent_id,))
                
                last_backup_date = None
                last_backup_duration_minutes = None
                last_backup_duration_seconds = None
                is_slow_backup = False
                is_old_backup = False
                last_screenshot_url = None
                
                # Get latest screenshot for this agent
                latest_screenshot = self.database.execute_query("""
                    SELECT verify_boot_screenshot_url 
                    FROM snapshots 
                    WHERE agent_id = ? 
                      AND verify_boot_screenshot_url IS NOT NULL 
                      AND verify_boot_screenshot_url != ''
                    ORDER BY backup_started_at DESC
                    LIMIT 1
                """, (agent_id,))
                
                if latest_screenshot:
                    last_screenshot_url = latest_screenshot[0]['verify_boot_screenshot_url']
                
                if last_successful_backup:
                    backup = last_successful_backup[0]
                    
                    # Format backup date with absolute date/time
                    if backup.get('started_at'):
                        backup_dt = self._parse_datetime(backup['started_at'])
                        if backup_dt:
                            last_backup_date = self._format_datetime_absolute(backup_dt, user_tz)
                            
                            # Check if backup is old (>7 days)
                            now = datetime.utcnow()
                            if now.tzinfo is None:
                                from datetime import timezone as tz_utc
                                now = now.replace(tzinfo=tz_utc.utc)
                            if backup_dt.tzinfo is None:
                                backup_dt = backup_dt.replace(tzinfo=tz_utc.utc)
                            
                            days_since_backup = (now - backup_dt).days
                            if days_since_backup > 7:
                                is_old_backup = True
                                old_backup_count += 1
                    
                    # Calculate backup duration
                    if backup.get('started_at') and backup.get('ended_at'):
                        start_dt = self._parse_datetime(backup['started_at'])
                        end_dt = self._parse_datetime(backup['ended_at'])
                        if start_dt and end_dt:
                            duration = end_dt - start_dt
                            duration_seconds = int(duration.total_seconds())
                            duration_minutes = int(duration_seconds / 60)
                            
                            last_backup_duration_minutes = duration_minutes
                            last_backup_duration_seconds = duration_seconds
                            
                            # Check if backup is slow (>30 minutes)
                            if duration_minutes > 30:
                                is_slow_backup = True
                                slow_backup_count += 1
                
                # Determine if agent config is an outlier
                config_outlier = False
                agent_os_version = f"{agent.get('os')} {agent.get('os_version')}" if agent.get('os') and agent.get('os_version') else None
                
                if most_common_os and agent_os_version and agent_os_version != most_common_os:
                    config_outlier = True
                elif most_common_encryption and agent.get('encryption_algorithm') and agent.get('encryption_algorithm') != most_common_encryption:
                    config_outlier = True
                elif most_common_agent_version and agent.get('agent_version') and agent.get('agent_version') != most_common_agent_version:
                    config_outlier = True
                elif most_common_platform and agent.get('platform') and agent.get('platform') != most_common_platform:
                    config_outlier = True
                
                if config_outlier:
                    config_outlier_count += 1
                
                # Format IP addresses (parse JSON array and join)
                ip_addresses_formatted = 'N/A'
                if agent.get('ip_addresses'):
                    try:
                        import json
                        ip_list = json.loads(agent['ip_addresses'])
                        if ip_list:
                            ip_addresses_formatted = ', '.join(ip_list)
                    except Exception:
                        ip_addresses_formatted = agent.get('ip_addresses', 'N/A')
                
                # Format last_seen_at with absolute date/time
                last_seen_formatted = 'N/A'
                if agent.get('last_seen_at'):
                    try:
                        last_seen_dt = self._parse_datetime(agent['last_seen_at'])
                        if last_seen_dt:
                            last_seen_formatted = self._format_datetime_absolute(last_seen_dt, user_tz)
                    except Exception:
                        last_seen_formatted = agent.get('last_seen_at', 'N/A')
                
                agent_list.append({
                    'agent_info': dict(agent),
                    'last_successful_backup_date': last_backup_date,
                    'last_backup_duration_minutes': last_backup_duration_minutes,
                    'last_backup_duration_seconds': last_backup_duration_seconds,
                    'is_slow_backup': is_slow_backup,
                    'is_old_backup': is_old_backup,
                    'config_outlier': config_outlier,
                    'ip_addresses_formatted': ip_addresses_formatted,
                    'last_seen_formatted': last_seen_formatted,
                    'last_screenshot_url': last_screenshot_url
                })
            
            # Format device IP addresses (parse JSON array and join)
            device_ip_formatted = 'N/A'
            if device.get('ip_addresses'):
                try:
                    import json
                    ip_list = json.loads(device['ip_addresses'])
                    if ip_list:
                        device_ip_formatted = ', '.join(ip_list)
                except Exception:
                    device_ip_formatted = device.get('ip_addresses', 'N/A')
            
            device_info_with_formatted = dict(device)
            device_info_with_formatted['ip_addresses_formatted'] = device_ip_formatted
            
            device_list.append({
                'device_info': device_info_with_formatted,
                'agents': agent_list
            })
        
        return {
            'agent_config_overview': {
                'devices': device_list,
                'summary': {
                    'total_devices': len(devices),
                    'total_agents': total_agents,
                    'slow_backup_count': slow_backup_count,
                    'old_backup_count': old_backup_count,
                    'config_outlier_count': config_outlier_count
                }
            }
        }
    
    @staticmethod
    def _format_datetime_absolute(dt: datetime, tz: pytz.timezone) -> str:
        """
        Format datetime in absolute format: 1:24PM Oct 4th 2025 EDT
        
        Args:
            dt: Datetime to format
            tz: User's timezone
            
        Returns:
            Formatted date string
        """
        if not dt:
            return 'N/A'
        
        # Convert to user timezone
        if dt.tzinfo is None:
            from datetime import timezone as tz_utc
            dt = dt.replace(tzinfo=tz_utc.utc)
        
        local_dt = dt.astimezone(tz)
        
        # Get ordinal suffix for day
        day = local_dt.day
        if 10 <= day % 100 <= 20:
            suffix = 'th'
        else:
            suffix = {1: 'st', 2: 'nd', 3: 'rd'}.get(day % 10, 'th')
        
        # Format: 1:24PM Oct 4th 2025 EDT
        time_str = local_dt.strftime('%-I:%M%p')  # 1:24PM
        date_str = local_dt.strftime('%b')  # Oct
        day_str = f"{day}{suffix}"  # 4th
        year_str = local_dt.strftime('%Y')  # 2025
        tz_str = local_dt.strftime('%Z')  # EDT
        
        return f"{time_str} {date_str} {day_str} {year_str} {tz_str}"
    
    @staticmethod
    def _format_bytes(bytes_val: int) -> str:
        """Format bytes for human-readable display"""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if bytes_val < 1024.0:
                return f"{bytes_val:.1f} {unit}"
            bytes_val /= 1024.0
        return f"{bytes_val:.1f} PB"

