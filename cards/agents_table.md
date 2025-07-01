# Agents Overview

| Agent Name | Client | Device | Operating System | Status | Last Seen |
|------------|--------|--------|------------------|---------|-----------|
{{#each agents}}
| {{display_name || hostname}} | {{client_name}} | {{device_display_name || device_hostname}} | {{platform_short}} | {{status_indicator}} | {{time_since_last_seen}} |
{{/each}}

<!-- TEMPLATE END - LLM STOP HERE -->
<!-- The content below is documentation only and should not be included in generated output -->

---

## Template Variables

- `{{display_name}}` - Agent's display name (may be empty)
- `{{hostname}}` - Agent's hostname (fallback identifier)
- `{{client_name}}` - Name of the client this agent belongs to
- `{{device_display_name}}` - Display name of the backup device
- `{{device_hostname}}` - Hostname of the backup device (fallback)
- `{{platform_short}}` - Shortened OS description (e.g., "Windows Server 2022", "Windows 11 Pro")
- `{{status_indicator}}` - Status with emoji (🟢 Online, 🟡 Recent, 🔴 Offline)
- `{{time_since_last_seen}}` - Human-readable time since last seen

## Example Output

| Agent Name | Client | Device | Operating System | Status | Last Seen |
|------------|--------|--------|------------------|---------|-----------|
| Acme-SQL01 | Acme | Acme-bkp | Windows Server 2022 | 🟢 Online | 2 min ago |
| Acme-Print | Acme | Acme-bkp | Windows Server 2022 | 🟢 Online | 1 min ago |
| Acme-HQ-PC02 | Acme | Acme-bkp | Windows 10 Home | 🟢 Online | 3 min ago |
| Acme-HQ-PC01 | Acme | Acme-bkp | Windows 10 Home | 🟢 Online | 2 min ago |
| Acme-HQ-LT01 | Acme | Acme-bkp | Windows 11 Pro | 🟢 Online | 2 min ago |
| Acme-FS01 | Acme | Acme-bkp | Windows Server 2022 | 🟢 Online | 3 min ago |
| Acme-DC01 | Acme | Acme-bkp | Windows Server 2022 | 🟢 Online | 3 min ago |
| Veridian-HQ-Jabberwocky | Veridian Dynamics | Veridian-bkp | Windows Server 2022 | 🟢 Online | 2 min ago |
| Veridian-HQ-Files | Veridian Dynamics | Veridian-bkp | Windows Server 2022 | 🟢 Online | 1 min ago |
| Veridian-HQ-DC01 | Veridian Dynamics | Veridian-bkp | Windows Server 2022 | 🟢 Online | 1 min ago |

## Usage Notes

This table format is ideal for:
- Getting an overview of all agents across multiple clients
- Quickly identifying offline or problematic agents
- Comparing agent status and activity patterns
- Sorting and filtering agents by client, device, or status

The table prioritizes the most important information while keeping it compact enough to display many agents at once. 