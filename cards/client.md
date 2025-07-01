# Client: {{name}}

## Overview
- **Client Name:** {{name}}
- **Number of Devices:** {{device_count}}
- **Total Agents:** {{total_agent_count}}
- **Comments:** {{comments || "None"}}

## Devices
{{#each devices}}
### {{display_name || hostname}}
- **Hostname:** {{hostname}}
- **Status:** {{service_status_indicator}} {{service_status}}
- **Last Seen:** {{last_seen_at | format_datetime}}
- **Agents:** {{agent_count}} connected

{{/each}}

<!-- TEMPLATE END - LLM STOP HERE -->
<!-- The content below is documentation only and should not be included in generated output -->

---

## Template Variables
IMPORTANT: you should call list_all_clients_devices_and_agents to get context

- `{{name}}` - Client name
- `{{device_count}}` - Number of devices for this client
- `{{total_agent_count}}` - Total number of agents across all devices
- `{{comments}}` - Client comments/notes
- `{{devices}}` - Array of device objects
- `{{display_name}}` - Device display name
- `{{hostname}}` - Device hostname
- `{{service_status}}` - Device service status
- `{{service_status_indicator}}` - Status emoji
- `{{last_seen_at}}` - Device last seen timestamp
- `{{agent_count}}` - Number of agents on this device 