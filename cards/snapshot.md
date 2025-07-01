# Snapshot: {{agent_hostname}} - {{backup_date}}

## Snapshot Information
- **Agent:** {{agent_hostname}}
- **Created:** {{backup_started_at | format_datetime}}
- **Duration:** {{backup_duration}}
- **Screenshot:** <img src="{{verify_boot_screenshot_url}}" alt="Boot Screenshot" width="150" height="100" style="border: 1px solid #ddd; border-radius: 4px;" />

## Verification Status
- **Boot Verification:** {{boot_status_indicator}} {{verify_boot_status}}
- **Filesystem Verification:** {{fs_status_indicator}} {{verify_fs_status}}

## Storage Locations
{{#each locations}}
- **{{type | capitalize}}:** {{location_description}}
{{/each}}

## Restore Options
This snapshot can be restored as:
- Files and folders
- Full system image  
- Virtual machine ({{vm_deployment_options}})

<!-- TEMPLATE END - LLM STOP HERE -->
<!-- The content below is documentation only and should not be included in generated output -->

---

## Template Variables
IMPORTANT: you should call list_all_clients_devices_and_agents to get context

- `{{agent_hostname}}` - Hostname of the agent this snapshot belongs to
- `{{backup_date}}` - Human-readable backup date
- `{{backup_started_at}}` - ISO timestamp when backup started
- `{{backup_duration}}` - Human-readable backup duration
- `{{verify_boot_screenshot_url}}` - URL to boot verification screenshot
- `{{boot_status_indicator}}` - ✅ for success, ❌ for failure
- `{{verify_boot_status}}` - Boot verification status text
- `{{fs_status_indicator}}` - ✅ for success, ❌ for failure  
- `{{verify_fs_status}}` - Filesystem verification status text
- `{{locations}}` - Array of storage location objects
- `{{type}}` - Location type (local, cloud)
- `{{location_description}}` - Human-readable location description
- `{{vm_deployment_options}}` - Available VM deployment options (local/cloud) 