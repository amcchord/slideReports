# Clients Overview

| Client Name | Devices | Total Agents | Status | Comments |
|-------------|---------|--------------|---------|----------|
{{#each clients}}
| {{name}} | {{device_count}} | {{total_agent_count}} | {{overall_status_indicator}} | {{comments || "—"}} |
{{/each}}

<!-- TEMPLATE END - LLM STOP HERE -->
<!-- The content below is documentation only and should not be included in generated output -->

---

## Template Variables
IMPORTANT: you should call list_all_clients_devices_and_agents to get context


- `{{name}}` - Client name
- `{{device_count}}` - Number of devices for this client
- `{{total_agent_count}}` - Total number of agents across all devices
- `{{overall_status_indicator}}` - Overall client status emoji
- `{{comments}}` - Client comments/notes 