# Snapshots Overview

| Agent | Created | Verification | Storage | Screenshot |
|-------|---------|--------------|---------|------------|
{{#each snapshots}}
| {{agent_hostname}} | {{backup_started_at | format_date_short}} | {{verification_status}} | {{storage_summary}} | <a href="{{verify_boot_screenshot_url}}" target="_blank"><img src="{{verify_boot_screenshot_url}}" alt="Boot Screenshot" width="50" height="30" style="border: 1px solid #ddd; border-radius: 2px;" /></a> |
{{/each}}

<!-- TEMPLATE END - LLM STOP HERE -->
<!-- The content below is documentation only and should not be included in generated output -->

---

## Template Variables
- `{{agent_hostname}}` - Hostname of the agent this snapshot belongs to
- `{{backup_started_at}}` - ISO timestamp when backup started
- `{{verification_status}}` - Combined boot and FS verification status with emojis
- `{{storage_summary}}` - Simplified storage location summary (e.g., "Local + Cloud")
- `{{verify_boot_screenshot_url}}` - URL to boot verification screenshot (used as clickable thumbnail) 