# Daily Backup Report - {{REPORT_DATE}}

> **Snapshot Status and Verification Summary**  
> Server Agents → Backup Devices → Cloud Storage

---

## 📊 Report Summary

| Metric | Count |
|--------|-------|
| **Successful Snapshots** | {{TOTAL_SUCCESSFUL_SNAPSHOTS}} |
| **Failed Snapshots** | {{TOTAL_FAILED_SNAPSHOTS}} |
| **Active Clients** | {{TOTAL_CLIENTS}} |
| **Total Devices** | {{TOTAL_DEVICES}} |

---

## 🔄 System Health

| Component | Status |
|-----------|--------|
| **Agents Online** | {{AGENTS_ONLINE}}/{{TOTAL_AGENTS}} |
| **Devices Active** | {{DEVICES_ACTIVE}}/{{TOTAL_DEVICES}} |
| **Cloud Sync** | {{CLOUD_SYNC_STATUS}} |

## 📈 Today's Activity

| Metric | Value |
|--------|-------|
| **Snapshots Created** | {{SNAPSHOTS_TODAY}} |
| **Data Transferred** | {{DATA_TRANSFERRED_TODAY}} |
| **Average Snapshot Size** | {{AVG_SNAPSHOT_SIZE}} |

---

## 👥 Client Reports

### 🏢 {{CLIENT1_NAME}}

**Summary:** {{CLIENT1_SUCCESSFUL_SNAPSHOTS}} Successful • {{CLIENT1_FAILED_SNAPSHOTS}} Failed

#### 💾 Device: {{CLIENT1_DEVICE1_NAME}}
- **Storage Usage:** {{CLIENT1_DEVICE1_STORAGE_USED}} / {{CLIENT1_DEVICE1_STORAGE_TOTAL}}
- **Location:** {{CLIENT1_DEVICE1_LOCATION}}

##### 🖥️ Servers Backing Up to This Device

**Server:** {{CLIENT1_DEVICE1_AGENT1_SERVER_NAME}}  
**Agent:** {{CLIENT1_DEVICE1_AGENT1_NAME}}

| Detail | Value |
|--------|-------|
| **Snapshots Today** | {{CLIENT1_DEVICE1_AGENT1_SNAPSHOT_COUNT}} |
| **Last Snapshot** | {{CLIENT1_DEVICE1_AGENT1_LAST_BACKUP_TIME}} |
| **Agent Status** | {{CLIENT1_DEVICE1_AGENT1_STATUS}} |
| **Total Size** | {{CLIENT1_DEVICE1_AGENT1_TOTAL_SIZE}} |
| **Cloud Sync** | {{CLIENT1_DEVICE1_AGENT1_CLOUD_STATUS}} |
| **Server IP** | {{CLIENT1_DEVICE1_AGENT1_SERVER_IP}} |

**Latest Screenshot:** Taken at {{CLIENT1_DEVICE1_AGENT1_SCREENSHOT_TIME}}

---

**Additional Agents:** {{CLIENT1_DEVICE1_ADDITIONAL_AGENTS}}

**Additional Devices:** {{CLIENT1_ADDITIONAL_DEVICES}}

---

**Additional Clients:** {{ADDITIONAL_CLIENTS}}

---

## ⚠️ Failed Snapshots Requiring Attention

{{FAILED_SNAPSHOT_DETAILS}}

---

## 📊 Storage Trends

### Storage Usage by Client
{{CLIENT1_NAME}}: {{CLIENT1_TOTAL_STORAGE}} GB  
{{CLIENT2_NAME}}: {{CLIENT2_TOTAL_STORAGE}} GB  
{{CLIENT3_NAME}}: {{CLIENT3_TOTAL_STORAGE}} GB  

### Daily Backup Volume Trend
- 6 days ago: 45 GB
- 5 days ago: 52 GB  
- 4 days ago: 48 GB
- 3 days ago: 61 GB
- 2 days ago: 55 GB
- Yesterday: 58 GB
- Today: {{TODAY_BACKUP_VOLUME}} GB

---

## 📝 Report Notes & Recommendations

### Issues Identified
{{IDENTIFIED_ISSUES}}

### Recommendations  
{{RECOMMENDATIONS}}

### Action Items
{{ACTION_ITEMS}}

---

**Report Generated:** {{GENERATION_TIMESTAMP}}  
**Automated backup monitoring and verification system** 