# Device: {{display_name || hostname}}

## Device Information
- **Display Name:** {{display_name || "Not set"}}
- **Hostname:** {{hostname}}
- **Service Status:** {{service_status_indicator}} {{service_status}}
- **Last Seen:** {{last_seen_at | format_datetime}}

## Client Assignment
- **Client:** {{client_name}}

## Connected Agents ({{agent_count}})
{{#each agents}}
### {{display_name || hostname}}
- **Hostname:** {{hostname}}
- **Operating System:** {{platform}}
- **Status:** {{status_indicator}} {{time_since_last_seen}}

{{/each}}

<!-- TEMPLATE END - LLM STOP HERE -->
<!-- The content below is documentation only and should not be included in generated output -->

---

## Template Variables
IMPORTANT: you should call list_all_clients_devices_and_agents to get context


- `{{display_name}}` - Device display name (may be empty)
- `{{hostname}}` - Device hostname
- `{{service_status}}` - Device service status (active, inactive, etc.)
- `{{service_status_indicator}}` - Status emoji
- `{{last_seen_at}}` - Device last seen timestamp
- `{{client_name}}` - Name of client this device belongs to
- `{{agent_count}}` - Number of connected agents
- `{{agents}}` - Array of agent objects
- `{{platform}}` - Agent OS platform
- `{{status_indicator}}` - Agent status emoji
- `{{time_since_last_seen}}` - Human-readable time since agent last seen 