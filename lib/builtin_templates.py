"""
Built-in recipe templates that are available to all users.
These templates are stored in code rather than database to ensure they're always available.
"""
from typing import List, Dict, Any


def get_builtin_templates() -> List[Dict[str, Any]]:
    """
    Get list of built-in template dictionaries.
    
    Built-in templates use negative IDs to avoid conflicts with user templates.
    
    Returns:
        List of template dictionaries with keys: template_id, name, description, html_content, is_builtin
    """
    return [
        {
            'template_id': -1,
            'name': 'Weekly Report',
            'description': 'Professional weekly backup report with 7-day calendar grids, screenshot comparisons, and storage growth metrics',
            'html_content': _get_weekly_template_html(),
            'is_builtin': True,
            'is_default': True,
            'created_at': '2025-10-15T00:00:00.000000',
            'updated_at': '2025-10-15T00:00:00.000000'
        },
        {
            'template_id': -2,
            'name': 'Monthly Report',
            'description': 'Professional monthly backup report with full-month calendar grids, screenshot comparisons, and storage growth metrics',
            'html_content': _get_monthly_template_html(),
            'is_builtin': True,
            'is_default': False,
            'created_at': '2025-10-15T00:00:00.000000',
            'updated_at': '2025-10-15T00:00:00.000000'
        },
        {
            'template_id': -3,
            'name': 'Quarterly Report',
            'description': 'Professional quarterly backup report with 13-week overview, screenshot comparisons, and storage growth metrics',
            'html_content': _get_quarterly_template_html(),
            'is_builtin': True,
            'is_default': False,
            'created_at': '2025-10-15T00:00:00.000000',
            'updated_at': '2025-10-15T00:00:00.000000'
        },
        {
            'template_id': -4,
            'name': 'System Data and Configuration',
            'description': 'Configuration overview showing device and agent settings with outlier detection for backup performance and configuration differences',
            'html_content': _get_configs_template_html(),
            'is_builtin': True,
            'is_default': False,
            'created_at': '2025-10-15T00:00:00.000000',
            'updated_at': '2025-10-15T00:00:00.000000'
        },
        {
            'template_id': -5,
            'name': 'Audit Logs (coming soon)',
            'description': 'Comprehensive audit log report showing all system activities and changes during the report period',
            'html_content': _get_audit_logs_template_html(),
            'is_builtin': True,
            'is_default': False,
            'created_at': '2025-10-15T00:00:00.000000',
            'updated_at': '2025-10-15T00:00:00.000000'
        },
        {
            'template_id': -6,
            'name': 'Snapshot Audit',
            'description': 'Complete snapshot audit showing all snapshots by agent with verification status, location, and thumbnails',
            'html_content': _get_snapshot_audit_template_html(),
            'is_builtin': True,
            'is_default': False,
            'created_at': '2025-10-18T00:00:00.000000',
            'updated_at': '2025-10-18T00:00:00.000000'
        }
    ]


def get_builtin_template_by_id(template_id: int) -> Dict[str, Any]:
    """
    Get a specific built-in template by ID.
    
    Args:
        template_id: Negative integer ID of built-in template
        
    Returns:
        Template dictionary or None if not found
    """
    templates = get_builtin_templates()
    for template in templates:
        if template['template_id'] == template_id:
            return template
    return None


def _get_weekly_template_html() -> str:
    """Get HTML for weekly report template"""
    return _get_base_template_html()


def _get_monthly_template_html() -> str:
    """Get HTML for monthly report template"""
    return _get_base_template_html()


def _get_quarterly_template_html() -> str:
    """Get HTML for quarterly report template"""
    return _get_base_template_html()


def _get_configs_template_html() -> str:
    """Get HTML for configs report template"""
    return _get_configs_html()


def _get_audit_logs_template_html() -> str:
    """Get HTML for audit logs report template"""
    return _get_audit_logs_html()


def _get_snapshot_audit_template_html() -> str:
    """Get HTML for snapshot audit report template"""
    return _get_snapshot_audit_html()


def _get_configs_html() -> str:
    """
    Get the HTML template for the Configs report.
    Shows device and agent configuration details with outlier detection.
    """
    return """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Configuration Overview</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            line-height: 1.6;
            color: #1f2937;
            background: #ffffff;
            padding: 40px;
        }
        
        .report-header {
            border-bottom: 3px solid #3b82f6;
            padding-bottom: 20px;
            margin-bottom: 40px;
            display: flex;
            align-items: flex-start;
            gap: 30px;
        }
        
        .report-logo {
            max-width: 150px;
            height: auto;
            flex-shrink: 0;
        }
        
        .report-header-content {
            flex: 1;
        }
        
        .report-title {
            font-size: 32px;
            font-weight: 700;
            color: #1f2937;
            margin-bottom: 10px;
            margin-top: 0;
        }
        
        .report-meta {
            color: #6b7280;
            font-size: 14px;
        }
        
        .section {
            margin-bottom: 40px;
            page-break-inside: avoid;
        }
        
        .section-title {
            font-size: 24px;
            font-weight: 600;
            color: #1f2937;
            margin-bottom: 20px;
            border-bottom: 2px solid #e5e7eb;
            padding-bottom: 10px;
        }
        
        .metric-grid {
            display: flex;
            flex-wrap: wrap;
            gap: 20px;
            margin-bottom: 30px;
        }
        
        .metric-card {
            background: #f9fafb;
            border: 1px solid #e5e7eb;
            border-radius: 8px;
            padding: 20px;
            flex: 1 1 200px;
            min-width: 200px;
        }
        
        .metric-label {
            font-size: 12px;
            font-weight: 600;
            text-transform: uppercase;
            color: #6b7280;
            letter-spacing: 0.5px;
            margin-bottom: 8px;
        }
        
        .metric-value {
            font-size: 32px;
            font-weight: 700;
            color: #1f2937;
        }
        
        .metric-value.success {
            color: #047857;
        }
        
        .metric-value.warning {
            color: #b45309;
        }
        
        .metric-value.danger {
            color: #dc2626;
        }
        
        .device-section {
            background: #f9fafb;
            border: 1px solid #e5e7eb;
            border-radius: 8px;
            padding: 20px;
            margin-bottom: 25px;
            page-break-inside: avoid;
        }
        
        .device-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
            padding-bottom: 10px;
            border-bottom: 2px solid #e5e7eb;
        }
        
        .device-header-name {
            font-size: 20px;
            font-weight: 600;
            color: #1f2937;
        }
        
        .device-header-model {
            font-size: 14px;
            font-weight: 500;
            color: #6b7280;
        }
        
        .data-table {
            width: 100%;
            border-collapse: collapse;
            margin-bottom: 20px;
            background: white;
        }
        
        .data-table th {
            background: #f3f4f6;
            padding: 12px;
            text-align: left;
            font-weight: 600;
            font-size: 14px;
            color: #1f2937;
            border-bottom: 2px solid #d1d5db;
        }
        
        .data-table td {
            padding: 12px;
            border-bottom: 1px solid #e5e7eb;
            font-size: 14px;
        }
        
        .data-table tr:last-child td {
            border-bottom: none;
        }
        
        .data-table tr:hover {
            background: #f9fafb;
        }
        
        .config-label {
            font-weight: 600;
            color: #6b7280;
            width: 200px;
        }
        
        .agent-subsection {
            margin-top: 20px;
        }
        
        .agent-subsection-title {
            font-size: 16px;
            font-weight: 600;
            color: #374151;
            margin-bottom: 15px;
        }
        
        .agent-card {
            background: white;
            border: 2px solid #e5e7eb;
            border-radius: 8px;
            padding: 18px;
            margin-bottom: 15px;
        }
        
        .agent-card.slow-backup {
            border-color: #ef4444;
            background: #fef2f2;
        }
        
        .agent-card.old-backup {
            border-color: #f59e0b;
            background: #fffbeb;
        }
        
        .agent-card.config-outlier {
            border-color: #06b6d4;
            background: #ecfeff;
        }
        
        .agent-card-header {
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            margin-bottom: 15px;
            padding-bottom: 12px;
            border-bottom: 1px solid #e5e7eb;
            gap: 15px;
        }
        
        .agent-header-left {
            flex: 1;
            display: flex;
            flex-direction: column;
            gap: 8px;
        }
        
        .agent-name {
            font-size: 16px;
            font-weight: 600;
            color: #1f2937;
        }
        
        .agent-badges {
            display: flex;
            gap: 8px;
            flex-wrap: wrap;
        }
        
        .agent-screenshot {
            width: 96px;
            height: auto;
            border: 1px solid #d1d5db;
            border-radius: 4px;
            flex-shrink: 0;
        }
        
        .status-badge {
            display: inline-block;
            padding: 4px 12px;
            border-radius: 4px;
            font-size: 12px;
            font-weight: 600;
            text-transform: uppercase;
        }
        
        .status-danger {
            background: rgba(239, 68, 68, 0.15);
            color: #dc2626;
        }
        
        .status-warning {
            background: rgba(245, 158, 11, 0.15);
            color: #b45309;
        }
        
        .status-info {
            background: rgba(6, 182, 212, 0.15);
            color: #0891b2;
        }
        
        .agent-details {
            display: flex;
            flex-wrap: wrap;
            gap: 12px;
        }
        
        .detail-item {
            display: flex;
            flex-direction: column;
            flex: 1 1 250px;
            min-width: 250px;
        }
        
        .detail-label {
            font-size: 11px;
            font-weight: 600;
            text-transform: uppercase;
            color: #6b7280;
            letter-spacing: 0.5px;
            margin-bottom: 4px;
        }
        
        .detail-value {
            font-size: 13px;
            color: #1f2937;
            word-break: break-word;
        }
        
        .detail-value.highlight {
            font-weight: 600;
            color: #dc2626;
        }
        
        .no-agents {
            text-align: center;
            padding: 30px;
            color: #9ca3af;
            font-style: italic;
        }
        
        @media print {
            body {
                padding: 20px;
            }
            
            .section {
                page-break-inside: avoid;
            }
            
            @page {
                size: 1600px 2400px;
                margin: 20mm;
            }
        }
    </style>
</head>
<body>
    <div class="report-header">
        <img src="{{ logo_url }}" alt="Logo" class="report-logo">
        <div class="report-header-content">
            <h1 class="report-title">Configuration Overview</h1>
            <div class="report-meta">
                <strong>Generated:</strong> {{ generated_at }}<br>
                <strong>Timezone:</strong> {{ timezone }}
            </div>
        </div>
    </div>
    
    <div class="section">
        <h2 class="section-title">Summary</h2>
        <div class="metric-grid">
            <div class="metric-card">
                <div class="metric-label">Total Devices</div>
                <div class="metric-value">{{ agent_config_overview.summary.total_devices }}</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Total Agents</div>
                <div class="metric-value">{{ agent_config_overview.summary.total_agents }}</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Slow Backups (&gt;30min)</div>
                <div class="metric-value danger">{{ agent_config_overview.summary.slow_backup_count }}</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Old Backups (&gt;7d)</div>
                <div class="metric-value warning">{{ agent_config_overview.summary.old_backup_count }}</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Config Outliers</div>
                <div class="metric-value">{{ agent_config_overview.summary.config_outlier_count }}</div>
            </div>
        </div>
    </div>
    
    {% for device_group in agent_config_overview.devices %}
    <div class="device-section">
        <div class="device-header">
            <span class="device-header-name">Device: {{ device_group.device_info.display_name or device_group.device_info.hostname or device_group.device_info.device_id }}</span>
            {% if device_group.device_info.hardware_model_name %}
            <span class="device-header-model">{{ device_group.device_info.hardware_model_name }}</span>
            {% endif %}
        </div>
        
        <table class="data-table">
            <tr>
                <td class="config-label">Device ID</td>
                <td>{{ device_group.device_info.device_id }}</td>
            </tr>
            <tr>
                <td class="config-label">Hostname</td>
                <td>{{ device_group.device_info.hostname or 'N/A' }}</td>
            </tr>
            <tr>
                <td class="config-label">IP Addresses</td>
                <td>{{ device_group.device_info.ip_addresses_formatted }}</td>
            </tr>
            <tr>
                <td class="config-label">Storage</td>
                <td>
                    {% if device_group.device_info.storage_used_bytes and device_group.device_info.storage_total_bytes %}
                        {{ (device_group.device_info.storage_used_bytes / 1024**3)|round(1) }} GB / {{ (device_group.device_info.storage_total_bytes / 1024**3)|round(1) }} GB
                        ({{ ((device_group.device_info.storage_used_bytes / device_group.device_info.storage_total_bytes) * 100)|round(1) }}%)
                    {% else %}
                        N/A
                    {% endif %}
                </td>
            </tr>
            <tr>
                <td class="config-label">Service Status</td>
                <td>{{ device_group.device_info.service_status or 'N/A' }}</td>
            </tr>
            <tr>
                <td class="config-label">Hardware Model</td>
                <td>{{ device_group.device_info.hardware_model_name or 'N/A' }}</td>
            </tr>
            <tr>
                <td class="config-label">Image Version</td>
                <td>{{ device_group.device_info.image_version or 'N/A' }}</td>
            </tr>
            <tr>
                <td class="config-label">Last Seen</td>
                <td>{{ device_group.device_info.last_seen_at or 'N/A' }}</td>
            </tr>
        </table>
        
        <div class="agent-subsection">
            <div class="agent-subsection-title">Connected Agents ({{ device_group.agents|length }})</div>
            
            {% if device_group.agents %}
                {% for agent in device_group.agents %}
                <div class="agent-card {% if agent.is_slow_backup %}slow-backup{% elif agent.is_old_backup %}old-backup{% elif agent.config_outlier %}config-outlier{% endif %}">
                    <div class="agent-card-header">
                        <div class="agent-header-left">
                            <span class="agent-name">{{ agent.agent_info.display_name or agent.agent_info.hostname or agent.agent_info.agent_id }}</span>
                            <div class="agent-badges">
                                {% if agent.is_slow_backup %}
                                <span class="status-badge status-danger">Slow Backup</span>
                                {% endif %}
                                {% if agent.is_old_backup %}
                                <span class="status-badge status-warning">Old Backup</span>
                                {% endif %}
                                {% if agent.config_outlier %}
                                <span class="status-badge status-info">Config Outlier</span>
                                {% endif %}
                            </div>
                        </div>
                        {% if agent.last_screenshot_url %}
                        <img src="{{ agent.last_screenshot_url }}" alt="Latest snapshot" class="agent-screenshot">
                        {% endif %}
                    </div>
                    
                    <div class="agent-details">
                        <div class="detail-item">
                            <div class="detail-label">Agent ID</div>
                            <div class="detail-value">{{ agent.agent_info.agent_id }}</div>
                        </div>
                        <div class="detail-item">
                            <div class="detail-label">Hostname</div>
                            <div class="detail-value">{{ agent.agent_info.hostname or 'N/A' }}</div>
                        </div>
                        <div class="detail-item">
                            <div class="detail-label">Operating System</div>
                            <div class="detail-value">{{ agent.agent_info.os or 'N/A' }}</div>
                        </div>
                        <div class="detail-item">
                            <div class="detail-label">OS Version</div>
                            <div class="detail-value">{{ agent.agent_info.os_version or 'N/A' }}</div>
                        </div>
                        <div class="detail-item">
                            <div class="detail-label">Platform</div>
                            <div class="detail-value">{{ agent.agent_info.platform or 'N/A' }}</div>
                        </div>
                        <div class="detail-item">
                            <div class="detail-label">Agent Version</div>
                            <div class="detail-value">{{ agent.agent_info.agent_version or 'N/A' }}</div>
                        </div>
                        <div class="detail-item">
                            <div class="detail-label">Encryption</div>
                            <div class="detail-value">{{ agent.agent_info.encryption_algorithm or 'N/A' }}</div>
                        </div>
                        <div class="detail-item">
                            <div class="detail-label">Firmware Type</div>
                            <div class="detail-value">{{ agent.agent_info.firmware_type or 'N/A' }}</div>
                        </div>
                        <div class="detail-item">
                            <div class="detail-label">Manufacturer</div>
                            <div class="detail-value">{{ agent.agent_info.manufacturer or 'N/A' }}</div>
                        </div>
                        <div class="detail-item">
                            <div class="detail-label">Sealed</div>
                            <div class="detail-value">{{ 'Yes' if agent.agent_info.sealed else 'No' }}</div>
                        </div>
                        <div class="detail-item">
                            <div class="detail-label">VSS Writers</div>
                            <div class="detail-value">{{ 'Configured' if agent.agent_info.vss_writer_configs else 'None' }}</div>
                        </div>
                        <div class="detail-item">
                            <div class="detail-label">Passphrases</div>
                            <div class="detail-value">{{ 'Configured' if agent.agent_info.passphrases else 'None' }}</div>
                        </div>
                        <div class="detail-item">
                            <div class="detail-label">IP Addresses</div>
                            <div class="detail-value">{{ agent.ip_addresses_formatted }}</div>
                        </div>
                        <div class="detail-item">
                            <div class="detail-label">Last Seen</div>
                            <div class="detail-value">{{ agent.last_seen_formatted }}</div>
                        </div>
                        <div class="detail-item">
                            <div class="detail-label">Last Successful Backup</div>
                            <div class="detail-value {% if agent.is_old_backup %}highlight{% endif %}">
                                {{ agent.last_successful_backup_date or 'Never' }}
                            </div>
                        </div>
                        <div class="detail-item">
                            <div class="detail-label">Last Backup Duration</div>
                            <div class="detail-value {% if agent.is_slow_backup %}highlight{% endif %}">
                                {% if agent.last_backup_duration_seconds is not none %}
                                    {% if agent.last_backup_duration_seconds < 60 %}
                                        {{ agent.last_backup_duration_seconds }} seconds
                                    {% else %}
                                        {{ agent.last_backup_duration_minutes }} minutes
                                    {% endif %}
                                {% else %}
                                    N/A
                                {% endif %}
                            </div>
                        </div>
                    </div>
                </div>
                {% endfor %}
            {% else %}
                <div class="no-agents">No agents connected to this device</div>
            {% endif %}
        </div>
    </div>
    {% endfor %}
    
    {% if not agent_config_overview.devices %}
    <div class="section">
        <div class="no-agents">No devices found in the system</div>
    </div>
    {% endif %}
</body>
</html>"""


def _get_base_template_html() -> str:
    """
    Get the base HTML template used for all built-in templates.
    This includes calendar grids, screenshot comparisons, and storage growth.
    """
    return """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Slide Backup Report</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            line-height: 1.6;
            color: #1f2937;
            background: #ffffff;
            padding: 40px;
        }
        
        .report-header {
            border-bottom: 3px solid #3b82f6;
            padding-bottom: 20px;
            margin-bottom: 40px;
            display: flex;
            align-items: flex-start;
            gap: 30px;
        }
        
        .report-logo {
            max-width: 150px;
            height: auto;
            flex-shrink: 0;
        }
        
        .report-header-content {
            flex: 1;
        }
        
        .report-title {
            font-size: 32px;
            font-weight: 700;
            color: #1f2937;
            margin-bottom: 10px;
            margin-top: 0;
        }
        
        .report-meta {
            color: #6b7280;
            font-size: 14px;
        }
        
        .section {
            margin-bottom: 40px;
            page-break-inside: avoid;
        }
        
        .section-title {
            font-size: 24px;
            font-weight: 600;
            color: #1f2937;
            margin-bottom: 20px;
            border-bottom: 2px solid #e5e7eb;
            padding-bottom: 10px;
        }
        
        .metric-grid {
            display: flex;
            flex-wrap: wrap;
            gap: 20px;
            margin-bottom: 30px;
        }
        
        .metric-card {
            background: #f9fafb;
            border: 1px solid #e5e7eb;
            border-radius: 8px;
            padding: 20px;
            flex: 1 1 200px;
            min-width: 200px;
        }
        
        .metric-label {
            font-size: 12px;
            font-weight: 600;
            text-transform: uppercase;
            color: #6b7280;
            letter-spacing: 0.5px;
            margin-bottom: 8px;
        }
        
        .metric-value {
            font-size: 32px;
            font-weight: 700;
            color: #1f2937;
        }
        
        .metric-value.success {
            color: #047857;
        }
        
        .metric-value.warning {
            color: #b45309;
        }
        
        .metric-value.danger {
            color: #dc2626;
        }
        
        .data-table {
            width: 100%;
            border-collapse: collapse;
            margin-bottom: 20px;
        }
        
        .data-table th {
            background: #f3f4f6;
            padding: 12px;
            text-align: left;
            font-weight: 600;
            font-size: 14px;
            color: #1f2937;
            border-bottom: 2px solid #d1d5db;
        }
        
        .data-table td {
            padding: 12px;
            border-bottom: 1px solid #e5e7eb;
            font-size: 14px;
        }
        
        .data-table tr:last-child td {
            border-bottom: none;
        }
        
        .data-table tr:hover {
            background: #f9fafb;
        }
        
        .status-badge {
            display: inline-block;
            padding: 4px 12px;
            border-radius: 4px;
            font-size: 12px;
            font-weight: 600;
            text-transform: uppercase;
        }
        
        .status-success {
            background: rgba(16, 185, 129, 0.15);
            color: #047857;
        }
        
        .status-warning {
            background: rgba(245, 158, 11, 0.15);
            color: #b45309;
        }
        
        .status-danger {
            background: rgba(239, 68, 68, 0.15);
            color: #dc2626;
        }
        
        .progress-bar {
            width: 100%;
            height: 40px;
            background: #e5e7eb;
            border-radius: 4px;
            overflow: hidden;
            margin-top: 8px;
            position: relative;
        }
        
        .progress-fill {
            height: 100%;
            background: #3b82f6;
        }
        
        .progress-text {
            position: absolute;
            top: 0;
            right: 0;
            height: 100%;
            display: flex;
            align-items: center;
            padding-right: 16px;
            color: black;
            font-size: 18px;
            font-weight: 600;
            white-space: nowrap;
           
        }
        
        .summary-text {
            background: #f0f9ff;
            border-left: 4px solid #3b82f6;
            padding: 20px;
            margin-bottom: 20px;
            border-radius: 4px;
        }
        
        @media print {
            body {
                padding: 20px;
            }
            @page {
                size: 1600px 2400px;
                margin: 0.25in;
            }
            .section {
                page-break-inside: avoid;
            }
        }
    </style>
</head>
<body>
    <div class="report-header">
        <img src="{{ logo_url }}" alt="Logo" class="report-logo">
        <div class="report-header-content">
            <h1 class="report-title">{{ report_title }}</h1>
            <div class="report-meta">
                <strong>Report Period:</strong> {{ date_range }}<br>
                <strong>Generated:</strong> {{ generated_at }}<br>
                <strong>Timezone:</strong> {{ timezone }}
            </div>
        </div>
    </div>
    
    <div class="section">
        <h2 class="section-title">Executive Summary</h2>
        <div class="summary-text">
            {{ exec_summary }}
        </div>
    </div>
    
    {% if show_backup_stats %}
    <div class="section">
        <h2 class="section-title">Backup Statistics</h2>
        <div class="metric-grid">
            <div class="metric-card">
                <div class="metric-label">Total Backups</div>
                <div class="metric-value">{{ total_backups }}</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Successful</div>
                <div class="metric-value success">{{ successful_backups }}</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Failed</div>
                <div class="metric-value danger">{{ failed_backups }}</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Success Rate</div>
                <div class="metric-value">{{ success_rate }}%</div>
            </div>
        </div>
        
        <table class="data-table">
            <thead>
                <tr>
                    <th>Agent</th>
                    <th>Last Backup</th>
                    <th>Status</th>
                    <th>Duration</th>
                </tr>
            </thead>
            <tbody>
                {% for agent in agent_backup_status %}
                <tr>
                    <td>{{ agent.name }}</td>
                    <td>{{ agent.last_backup }}</td>
                    <td><span class="status-badge status-{{ agent.status_class }}">{{ agent.status }}</span></td>
                    <td>{{ agent.duration }}</td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
    </div>
    {% endif %}
    
    {% if show_snapshots %}
    <div class="section">
        <h2 class="section-title">Snapshot Overview</h2>
        <div class="metric-grid">
            <div class="metric-card">
                <div class="metric-label">Active Snapshot Times</div>
                <div class="metric-value">{{ active_snapshots }}</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Deleted Snapshots</div>
                <div class="metric-value">{{ deleted_snapshots }}</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Local Snapshots</div>
                <div class="metric-value">{{ local_snapshots }}</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Cloud Snapshots</div>
                <div class="metric-value">{{ cloud_snapshots }}</div>
            </div>
        </div>
        

    </div>
    {% endif %}
    
    {% if show_alerts %}
    <div class="section">
        <h2 class="section-title">Alerts Summary</h2>
        <div class="metric-grid">
            <div class="metric-card">
                <div class="metric-label">Total Alerts</div>
                <div class="metric-value">{{ total_alerts }}</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Unresolved</div>
                <div class="metric-value {% if unresolved_alerts == 0 %}success{% else %}danger{% endif %}">{{ unresolved_alerts }}</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Resolved</div>
                <div class="metric-value success">{{ resolved_alerts }}</div>
            </div>
        </div>
    </div>
    {% endif %}
    
    {% if show_storage %}
    <div class="section">
        <h2 class="section-title">Storage Usage</h2>
        {% for device in device_storage %}
        <div style="margin-bottom: 20px;">
            <strong>{{ device.name }}</strong>
            <div class="progress-bar">
                <div class="progress-fill" style="width: {{ device.percent }}%"></div>
                <div class="progress-text">
                    {{ device.used }} / {{ device.total }} ({{ device.percent }}%)
                </div>
            </div>
        </div>
        {% endfor %}
    </div>
    {% endif %}
    
    <div class="section">
        <h2 class="section-title">Snapshot Totals by Agent</h2>
        <table class="data-table">
            <thead>
                <tr>
                    <th>Agent</th>
                    <th>Local Snapshots</th>
                    <th>Cloud Snapshots</th>
                </tr>
            </thead>
            <tbody>
                {% for agent in agent_snapshot_totals %}
                <tr>
                    <td>{{ agent.agent_name }}</td>
                    <td>{{ agent.local_count }}</td>
                    <td>{{ agent.cloud_count }}</td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
    </div>
    
    <div class="section" style="page-break-before: always;">
        <h2 class="section-title">Backup Calendar by Agent</h2>
        {% for agent_cal in agent_calendars %}
        <div style="margin-bottom: 40px; page-break-inside: avoid;">
            <h3 style="font-size: 18px; margin-bottom: 15px; color: #1f2937;">{{ agent_cal.agent_name }}</h3>
            <table style="width: 100%; border-collapse: collapse; margin-bottom: 20px;">
                <thead>
                    <tr>
                        {% for day in agent_cal.calendar_grid[:7] %}
                        <th style="padding: 8px; text-align: center; font-size: 12px; font-weight: 600; color: #6b7280; border: 1px solid #e5e7eb;">
                            {{ day.day_of_week }}
                        </th>
                        {% endfor %}
                    </tr>
                </thead>
                <tbody>
                    <tr>
                        {% for day in agent_cal.calendar_grid %}
                        <td style="padding: 12px; position: relative; text-align: center; border: 1px solid #e5e7eb; 
                            {% if day.completion_color == 'green' %}background: #d1fae5; color: #065f46;
                            {% elif day.completion_color == 'yellow' %}background: #fef3c7; color: #92400e;
                            {% elif day.completion_color == 'red' %}background: #fee2e2; color: #991b1b;
                            {% else %}background: #f3f4f6; color: #9ca3af;
                            {% endif %}">
                            {% if day.day_number %}
                            <div style="position: absolute; top: 4px; right: 6px; font-size: 10px; font-weight: 600; color: #6b7280;">
                                {{ day.day_number }}
                            </div>
                            <div style="font-size: 11px; margin-top: 8px; opacity: 1;">
                                <div style="color: #2563eb;">{{ day.local_snapshots }} Local Snap</div>
                                <div style="color: #059669;">{{ day.cloud_snapshots }} Cloud Snap</div>
                            </div>
                            <div style="font-size: 9px; margin-top: 2px; font-weight: 600; opacity: 0.8;">
                                {% if day.snapshots_created > 0 %}{{ day.snapshots_created }} backups taken{% if day.snapshots_created != 1 %}s{% endif %}{% else %}-{% endif %}
                            </div>

                            {% endif %}
                        </td>
                        {% if loop.index is divisibleby 7 and not loop.last %}
                    </tr>
                    <tr>
                        {% endif %}
                        {% endfor %}
                    </tr>
                </tbody>
            </table>
        </div>
        {% endfor %}
    </div>
    
    {% if agent_screenshots %}
    <div class="section" style="page-break-before: always;">
        <h2 class="section-title">Snapshot Verification Screenshots</h2>
        <p style="margin-bottom: 20px; color: #6b7280;">Comparing oldest and newest snapshots from the reporting period</p>
        {% for agent in agent_screenshots %}
        <div style="margin-bottom: 30px; page-break-inside: avoid;">
            <h3 style="font-size: 18px; margin-bottom: 15px; color: #1f2937;">{{ agent.agent_name }}</h3>
            <div style="display: flex; flex-wrap: wrap; gap: 20px;">
                {% if agent.oldest_screenshot %}
                <div style="background: #f9fafb; padding: 12px; border-radius: 4px; border: 1px solid #e5e7eb; display: flex; gap: 12px; align-items: flex-start; flex: 1 1 400px; min-width: 400px;">
                    <img src="{{ agent.oldest_screenshot.url }}" alt="Oldest snapshot" style="width: 200px; height: auto; flex-shrink: 0; border: 1px solid #d1d5db; border-radius: 3px;">
                    <div style="flex: 1;">
                        <h4 style="font-size: 13px; margin: 0 0 8px 0; color: #6b7280; font-weight: 600;">Oldest Snapshot</h4>
                        <p style="font-size: 11px; margin: 0; color: #9ca3af; line-height: 1.4;">{{ agent.oldest_screenshot.date }}</p>
                    </div>
                </div>
                {% endif %}
                {% if agent.newest_screenshot %}
                <div style="background: #f9fafb; padding: 12px; border-radius: 4px; border: 1px solid #e5e7eb; display: flex; gap: 12px; align-items: flex-start; flex: 1 1 400px; min-width: 400px;">
                    <img src="{{ agent.newest_screenshot.url }}" alt="Newest snapshot" style="width: 200px; height: auto; flex-shrink: 0; border: 1px solid #d1d5db; border-radius: 3px;">
                    <div style="flex: 1;">
                        <h4 style="font-size: 13px; margin: 0 0 8px 0; color: #6b7280; font-weight: 600;">Newest Snapshot</h4>
                        <p style="font-size: 11px; margin: 0; color: #9ca3af; line-height: 1.4;">{{ agent.newest_screenshot.date }}</p>
                    </div>
                </div>
                {% endif %}
            </div>
        </div>
        {% endfor %}
    </div>
    {% endif %}
</body>
</html>"""


def _get_audit_logs_html() -> str:
    """
    Get the HTML template for the Audit Logs report.
    Shows comprehensive audit log activity for the reporting period.
    """
    return """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Audit Logs Report</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            line-height: 1.6;
            color: #1f2937;
            background: #ffffff;
            padding: 40px;
        }
        
        .report-header {
            border-bottom: 3px solid #3b82f6;
            padding-bottom: 20px;
            margin-bottom: 40px;
            display: flex;
            align-items: flex-start;
            gap: 30px;
        }
        
        .report-logo {
            max-width: 150px;
            height: auto;
            flex-shrink: 0;
        }
        
        .report-header-content {
            flex: 1;
        }
        
        .report-title {
            font-size: 32px;
            font-weight: 700;
            color: #1f2937;
            margin-bottom: 10px;
            margin-top: 0;
        }
        
        .report-meta {
            color: #6b7280;
            font-size: 14px;
        }
        
        .section {
            margin-bottom: 40px;
            page-break-inside: avoid;
        }
        
        .section-title {
            font-size: 24px;
            font-weight: 600;
            color: #1f2937;
            margin-bottom: 20px;
            border-bottom: 2px solid #e5e7eb;
            padding-bottom: 10px;
        }
        
        .metric-grid {
            display: flex;
            flex-wrap: wrap;
            gap: 20px;
            margin-bottom: 30px;
        }
        
        .metric-card {
            background: #f9fafb;
            border: 1px solid #e5e7eb;
            border-radius: 8px;
            padding: 20px;
            flex: 1 1 200px;
            min-width: 200px;
        }
        
        .metric-label {
            font-size: 12px;
            font-weight: 600;
            text-transform: uppercase;
            color: #6b7280;
            letter-spacing: 0.5px;
            margin-bottom: 8px;
        }
        
        .metric-value {
            font-size: 32px;
            font-weight: 700;
            color: #1f2937;
        }
        
        .metric-value.primary {
            color: #3b82f6;
        }
        
        .metric-value.success {
            color: #047857;
        }
        
        .metric-value.warning {
            color: #b45309;
        }
        
        .metric-value.danger {
            color: #dc2626;
        }
        
        .action-breakdown {
            display: flex;
            flex-wrap: wrap;
            gap: 15px;
            margin-bottom: 30px;
        }
        
        .action-item {
            background: #f9fafb;
            border: 1px solid #e5e7eb;
            border-radius: 6px;
            padding: 15px;
            text-align: center;
            flex: 1 1 150px;
            min-width: 150px;
        }
        
        .action-count {
            font-size: 24px;
            font-weight: 700;
            color: #1f2937;
            margin-bottom: 5px;
        }
        
        .action-name {
            font-size: 11px;
            font-weight: 600;
            text-transform: uppercase;
            color: #6b7280;
            letter-spacing: 0.5px;
        }
        
        .data-table {
            width: 100%;
            border-collapse: collapse;
            margin-bottom: 20px;
            background: white;
        }
        
        .data-table th {
            background: #f3f4f6;
            padding: 12px;
            text-align: left;
            font-weight: 600;
            font-size: 14px;
            color: #1f2937;
            border-bottom: 2px solid #d1d5db;
        }
        
        .data-table td {
            padding: 12px;
            border-bottom: 1px solid #e5e7eb;
            font-size: 14px;
            vertical-align: top;
        }
        
        .data-table tr:last-child td {
            border-bottom: none;
        }
        
        .data-table tr:hover {
            background: #f9fafb;
        }
        
        .data-table td.time-cell {
            white-space: nowrap;
            font-family: 'Courier New', monospace;
            font-size: 13px;
            color: #6b7280;
        }
        
        .data-table td.user-cell {
            font-weight: 500;
        }
        
        .data-table td.description-cell {
            color: #6b7280;
            font-size: 13px;
            max-width: 400px;
        }
        
        .status-badge {
            display: inline-block;
            padding: 4px 10px;
            border-radius: 4px;
            font-size: 11px;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        
        .badge-create {
            background: rgba(16, 185, 129, 0.15);
            color: #047857;
        }
        
        .badge-update {
            background: rgba(59, 130, 246, 0.15);
            color: #1e40af;
        }
        
        .badge-delete {
            background: rgba(239, 68, 68, 0.15);
            color: #dc2626;
        }
        
        .badge-login {
            background: rgba(139, 92, 246, 0.15);
            color: #6d28d9;
        }
        
        .badge-logout {
            background: rgba(107, 114, 128, 0.15);
            color: #374151;
        }
        
        .badge-default {
            background: rgba(107, 114, 128, 0.15);
            color: #4b5563;
        }
        
        .resource-badge {
            display: inline-block;
            padding: 2px 8px;
            border-radius: 3px;
            font-size: 11px;
            font-weight: 500;
            background: #e5e7eb;
            color: #4b5563;
        }
        
        .no-data {
            text-align: center;
            padding: 40px;
            color: #9ca3af;
            font-style: italic;
            background: #f9fafb;
            border-radius: 8px;
            border: 1px solid #e5e7eb;
        }
        
        @media print {
            body {
                padding: 20px;
            }
            
            .section {
                page-break-inside: avoid;
            }
            
            .data-table {
                page-break-inside: auto;
            }
            
            .data-table tr {
                page-break-inside: avoid;
                page-break-after: auto;
            }
            
            @page {
                size: 1300px 1800px;
                margin: 20mm;
            }
        }
    </style>
</head>
<body>
    <div class="report-header">
        <img src="{{ logo_url }}" alt="Logo" class="report-logo">
        <div class="report-header-content">
            <h1 class="report-title">Audit Logs Report</h1>
            <div class="report-meta">
                <strong>Report Period:</strong> {{ date_range }}<br>
                <strong>Generated:</strong> {{ generated_at }}<br>
                <strong>Timezone:</strong> {{ timezone }}
                {% if client_name %}
                <br><strong>Client:</strong> {{ client_name }}
                {% endif %}
            </div>
        </div>
    </div>
    
    <div class="section">
        <h2 class="section-title">Summary</h2>
        <div class="metric-grid">
            <div class="metric-card">
                <div class="metric-label">Total Audit Entries</div>
                <div class="metric-value primary">{{ total_audits }}</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Unique Actions</div>
                <div class="metric-value">{{ audit_actions|length }}</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Entries Shown</div>
                <div class="metric-value">{{ audits|length }}</div>
            </div>
        </div>
    </div>
    
    {% if audit_actions %}
    <div class="section">
        <h2 class="section-title">Activity Breakdown</h2>
        <div class="action-breakdown">
            {% for action, count in audit_actions.items() %}
            <div class="action-item">
                <div class="action-count">{{ count }}</div>
                <div class="action-name">{{ action }}</div>
            </div>
            {% endfor %}
        </div>
    </div>
    {% endif %}
    
    <div class="section">
        <h2 class="section-title">Detailed Audit Log</h2>
        
        {% if audits %}
        <table class="data-table">
            <thead>
                <tr>
                    <th style="width: 160px;">Time</th>
                    <th style="width: 140px;">User</th>
                    <th style="width: 120px;">Action</th>
                    <th style="width: 140px;">Resource Type</th>
                    <th>Resource ID / Description</th>
                </tr>
            </thead>
            <tbody>
                {% for audit in audits %}
                <tr>
                    <td class="time-cell">
                        {% if audit.audit_time %}
                            {{ audit.audit_time[:19].replace('T', ' ') }}
                        {% else %}
                            N/A
                        {% endif %}
                    </td>
                    <td class="user-cell">
                        {% if audit.user_id %}
                            {{ audit.user_id[:8] }}...
                        {% elif audit.system %}
                            <em>System</em>
                        {% else %}
                            Unknown
                        {% endif %}
                    </td>
                    <td>
                        {% if audit.action %}
                            {% set action_lower = audit.action.lower() %}
                            {% if 'create' in action_lower %}
                                <span class="status-badge badge-create">{{ audit.action }}</span>
                            {% elif 'update' in action_lower or 'edit' in action_lower or 'modify' in action_lower %}
                                <span class="status-badge badge-update">{{ audit.action }}</span>
                            {% elif 'delete' in action_lower or 'remove' in action_lower %}
                                <span class="status-badge badge-delete">{{ audit.action }}</span>
                            {% elif 'login' in action_lower %}
                                <span class="status-badge badge-login">{{ audit.action }}</span>
                            {% elif 'logout' in action_lower %}
                                <span class="status-badge badge-logout">{{ audit.action }}</span>
                            {% else %}
                                <span class="status-badge badge-default">{{ audit.action }}</span>
                            {% endif %}
                        {% else %}
                            <span class="status-badge badge-default">N/A</span>
                        {% endif %}
                    </td>
                    <td>
                        {% if audit.resource_type %}
                            <span class="resource-badge">{{ audit.resource_type }}</span>
                        {% else %}
                            <span style="color: #9ca3af;">—</span>
                        {% endif %}
                    </td>
                    <td class="description-cell">
                        {% if audit.resource_id %}
                            <strong>ID:</strong> {{ audit.resource_id[:16] }}{% if audit.resource_id|length > 16 %}...{% endif %}
                            <br>
                        {% endif %}
                        {% if audit.description %}
                            {{ audit.description }}
                        {% else %}
                            <span style="color: #9ca3af;">No description available</span>
                        {% endif %}
                    </td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
        
        {% if total_audits > audits|length %}
        <div style="text-align: center; padding: 20px; color: #6b7280; font-size: 14px; background: #f9fafb; border-radius: 6px; margin-top: 20px;">
            Showing {{ audits|length }} of {{ total_audits }} audit entries. 
            {% if total_audits > 100 %}
                (Limited to 100 most recent entries)
            {% endif %}
        </div>
        {% endif %}
        
        {% else %}
        <div class="no-data">
            No audit log entries found for the selected time period.
        </div>
        {% endif %}
    </div>
</body>
</html>"""


def _get_snapshot_audit_html() -> str:
    """
    Get the HTML template for the Snapshot Audit report.
    Shows complete list of snapshots by agent with verification status and thumbnails.
    """
    return """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Snapshot Audit Report</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            line-height: 1.6;
            color: #1f2937;
            background: #ffffff;
            padding: 40px;
        }
        
        .report-header {
            border-bottom: 3px solid #3b82f6;
            padding-bottom: 20px;
            margin-bottom: 40px;
            display: flex;
            align-items: flex-start;
            gap: 30px;
        }
        
        .report-logo {
            max-width: 150px;
            height: auto;
            flex-shrink: 0;
        }
        
        .report-header-content {
            flex: 1;
        }
        
        .report-title {
            font-size: 32px;
            font-weight: 700;
            color: #1f2937;
            margin-bottom: 10px;
            margin-top: 0;
        }
        
        .report-meta {
            color: #6b7280;
            font-size: 14px;
        }
        
        .section {
            margin-bottom: 40px;
            page-break-inside: avoid;
        }
        
        .section-title {
            font-size: 24px;
            font-weight: 600;
            color: #1f2937;
            margin-bottom: 20px;
            border-bottom: 2px solid #e5e7eb;
            padding-bottom: 10px;
        }
        
        .agent-section {
            margin-bottom: 40px;
            page-break-inside: avoid;
        }
        
        .agent-title {
            font-size: 20px;
            font-weight: 600;
            color: #1f2937;
            margin-bottom: 15px;
            padding: 12px 15px;
            background: #f3f4f6;
            border-left: 4px solid #3b82f6;
        }
        
        .data-table {
            width: 100%;
            border-collapse: collapse;
            margin-bottom: 20px;
            background: white;
        }
        
        .data-table th {
            background: #f3f4f6;
            padding: 12px;
            text-align: left;
            font-weight: 600;
            font-size: 14px;
            color: #1f2937;
            border: 1px solid #d1d5db;
        }
        
        .data-table td {
            padding: 12px;
            border: 1px solid #e5e7eb;
            font-size: 14px;
            vertical-align: middle;
        }
        
        .data-table tr:hover {
            background: #f9fafb;
        }
        
        .location-badge {
            display: inline-block;
            padding: 4px 10px;
            border-radius: 4px;
            font-size: 11px;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-right: 4px;
        }
        
        .badge-local {
            background: rgba(37, 99, 235, 0.15);
            color: #1e40af;
        }
        
        .badge-cloud {
            background: rgba(5, 150, 105, 0.15);
            color: #047857;
        }
        
        
        .verify-check {
            color: #047857;
            font-size: 18px;
            font-weight: 700;
        }
        
        .verify-none {
            color: #d1d5db;
            font-size: 14px;
        }
        
        .snapshot-thumbnail {
            width: 48px;
            height: 48px;
            object-fit: cover;
            border: 1px solid #d1d5db;
            border-radius: 3px;
        }
        
        .no-thumbnail {
            width: 48px;
            height: 48px;
            background: #f3f4f6;
            border: 1px solid #d1d5db;
            border-radius: 3px;
            display: flex;
            align-items: center;
            justify-content: center;
            color: #9ca3af;
            font-size: 10px;
        }
        
        .no-data {
            text-align: center;
            padding: 40px;
            color: #9ca3af;
            font-style: italic;
            background: #f9fafb;
            border-radius: 8px;
            border: 1px solid #e5e7eb;
        }
        
        .summary-box {
            background: #f0f9ff;
            border-left: 4px solid #3b82f6;
            padding: 20px;
            margin-bottom: 30px;
            border-radius: 4px;
        }
        
        .summary-box strong {
            color: #1e40af;
        }
        
        @media print {
            body {
                padding: 20px;
            }
            
            .section {
                page-break-inside: avoid;
            }
            
            .agent-section {
                page-break-inside: avoid;
            }
            
            .data-table {
                page-break-inside: auto;
            }
            
            .data-table tr {
                page-break-inside: avoid;
                page-break-after: auto;
            }
            
            @page {
                size: 1300px 1800px;
                margin: 20mm;
            }
        }
    </style>
</head>
<body>
    <div class="report-header">
        <img src="{{ logo_url }}" alt="Logo" class="report-logo">
        <div class="report-header-content">
            <h1 class="report-title">Snapshot Audit Report</h1>
            <div class="report-meta">
                <strong>Report Period:</strong> {{ date_range }}<br>
                <strong>Generated:</strong> {{ generated_at }}<br>
                <strong>Timezone:</strong> {{ timezone }}
                {% if client_name %}
                <br><strong>Client:</strong> {{ client_name }}
                {% endif %}
            </div>
        </div>
    </div>
    
    <div class="section">
        <h2 class="section-title">Summary</h2>
        <div class="summary-box">
            This report provides a complete audit of all snapshots within the specified date range.
            For each agent, you'll find detailed information about snapshot date/time, storage location,
            verification status, and screenshot thumbnails. Tables are designed to be Excel-friendly
            for easy copy/paste operations.
        </div>
    </div>
    
    {% if agent_snapshot_audit %}
        {% for agent_data in agent_snapshot_audit %}
        <div class="agent-section">
            <h3 class="agent-title">{{ agent_data.agent_name }} ({{ agent_data.snapshots|length }} snapshot{% if agent_data.snapshots|length != 1 %}s{% endif %})</h3>
            
            {% if agent_data.snapshots %}
            <table class="data-table">
                <thead>
                    <tr>
                        <th style="width: 200px;">Snapshot Date/Time</th>
                        <th style="width: 150px;">Location</th>
                        <th style="width: 120px; text-align: center;">Screenshot Verify</th>
                        <th style="width: 120px; text-align: center;">Filesystem Verify</th>
                        <th style="width: 60px; text-align: center;">Thumbnail</th>
                    </tr>
                </thead>
                <tbody>
                    {% for snapshot in agent_data.snapshots %}
                    <tr>
                        <td>{{ snapshot.date_formatted }}</td>
                        <td>
                            {% if snapshot.location_local %}
                                <span class="location-badge badge-local">Local</span>
                            {% endif %}
                            {% if snapshot.location_cloud %}
                                <span class="location-badge badge-cloud">Cloud</span>
                            {% endif %}
                        </td>
                        <td style="text-align: center;">
                            {% if snapshot.verify_boot_passed %}
                                <span class="verify-check">✓</span>
                            {% else %}
                                <span class="verify-none">—</span>
                            {% endif %}
                        </td>
                        <td style="text-align: center;">
                            {% if snapshot.verify_fs_passed %}
                                <span class="verify-check">✓</span>
                            {% else %}
                                <span class="verify-none">—</span>
                            {% endif %}
                        </td>
                        <td style="text-align: center;">
                            {% if snapshot.screenshot_url %}
                                <img src="{{ snapshot.screenshot_url }}" alt="Snapshot" class="snapshot-thumbnail">
                            {% else %}
                                <div class="no-thumbnail">N/A</div>
                            {% endif %}
                        </td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
            {% else %}
            <div class="no-data">No snapshots found for this agent in the selected period.</div>
            {% endif %}
        </div>
        {% endfor %}
    {% else %}
    <div class="section">
        <div class="no-data">No snapshot data found for the selected time period.</div>
    </div>
    {% endif %}
</body>
</html>"""

