# Devices Overview

| Device Name | Client | Hostname | Status | Agents | Last Seen |
|-------------|--------|----------|---------|---------|-----------|
{{#each devices}}
| {{display_name || hostname}} | {{client_name}} | {{hostname}} | {{service_status_indicator}} {{service_status}} | {{agent_count}} | {{time_since_last_seen}} |
{{/each}}

<!-- TEMPLATE END - LLM STOP HERE -->
<!-- The content below is documentation only and should not be included in generated output -->

---

## Template Variables
IMPORTANT: you should call list_all_clients_devices_and_agents to get context

- `{{display_name}}` - Device display name (may be empty)
- `{{hostname}}` - Device hostname (fallback identifier)
- `{{client_name}}` - Name of client this device belongs to
- `{{service_status}}` - Device service status
- `{{service_status_indicator}}` - Status emoji
- `{{agent_count}}` - Number of connected agents
- `{{time_since_last_seen}}` - Human-readable time since last seen 