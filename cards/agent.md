# Agent: {{display_name || hostname}}

## System Information
- **Hostname:** {{hostname}}
- **Operating System:** {{platform}}
- **OS Version:** {{os_version}}
- **Last Seen:** {{last_seen_at | format_datetime}}

## Status
- **Connection Status:** {{status_indicator}}
- **Last Activity:** {{time_since_last_seen}}

## Client & Device Assignment
- **Client:** {{client_name}}
- **Backup Device:** {{device_display_name || device_hostname}}

## Recent Backup Status
{{#each recent_backups}}
{{status_icon}} {{started_at | format_date}} ({{duration}})
{{/each}}

<!-- TEMPLATE END - LLM STOP HERE -->
<!-- The content below is documentation only and should not be included in generated output -->

---

## Template Variables
IMPORTANT: you should call list_all_clients_devices_and_agents to get context

- `{{display_name}}` - Agent's display name (may be empty)
- `{{hostname}}` - Agent's hostname (primary identifier)
- `{{platform}}` - Full OS platform description
- `{{os_version}}` - Operating system version
- `{{last_seen_at}}` - ISO timestamp of last connection
- `{{status_indicator}}` - Derived status (Online/Recently Active/Offline)
- `{{time_since_last_seen}}` - Human-readable time since last seen
- `{{client_name}}` - Name of the client this agent belongs to
- `{{device_display_name}}` - Display name of the backup device
- `{{device_hostname}}` - Hostname of the backup device
- `{{recent_backups}}` - Array of the last 5 backup jobs for this agent
- `{{status_icon}}` - ✅ for succeeded backups, ❌ for failed backups
- `{{started_at}}` - Backup start timestamp
- `{{duration}}` - Human-readable backup duration (e.g., "8s", "2m 15s")
