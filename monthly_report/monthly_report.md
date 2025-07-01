# Monthly Backup Report - {{REPORT_MONTH_YEAR}}

> **Comprehensive Monthly Snapshot Analysis & Retention Overview**  
> Daily Patterns • Retention Policies • Storage Trends

---

## 📊 Monthly Summary

| Metric | Count |
|--------|-------|
| **Total Snapshots** | {{TOTAL_MONTHLY_SNAPSHOTS}} |
| **Failed Snapshots** | {{TOTAL_FAILED_SNAPSHOTS}} |
| **Deleted (Retention)** | {{TOTAL_DELETED_SNAPSHOTS}} |
| **Active Days** | {{ACTIVE_DAYS}} |
| **Total Data Size** | {{TOTAL_DATA_SIZE}} |

---

## ⏰ Retention Policy Impact

### Current Retention Rules
{{RETENTION_RULES}}

### Snapshots Deleted This Month
- **Count:** {{SNAPSHOTS_DELETED_COUNT}}
- **Space Freed:** {{SPACE_FREED}}

### Upcoming Deletions
{{UPCOMING_DELETIONS}}

---

## 📅 Monthly Calendar View

> **Legend:**  
> ✅ Successful Snapshots • ❌ Failed Snapshots • 🗑️ Deleted (Retention)  
> 🟢 Good Status • 🟡 Warnings • 🔴 Errors • ⚪ Inactive

### Calendar Grid

{{CALENDAR_DAYS_GRID}}

#### Calendar Day Template Structure:
```
## Day X - {{DATE}}
**Status:** [🟢 Good | 🟡 Warning | 🔴 Error | ⚪ Inactive]

### Snapshot Summary
- ✅ Successful: X snapshots
- ❌ Failed: X snapshots  
- 🗑️ Deleted: X snapshots

### Details
- Client snapshots and agent details
- Specific issues or notes
- Retention actions performed
```

---

## 📈 Monthly Trends & Patterns

### Daily Snapshot Volume
**Daily snapshot counts for each day of the month:**

| Day | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 |
|-----|---|---|---|---|---|---|---|---|---|-----|
| Count | 15| 18| 16| 20| 17| 19| 14| 22| 18| 16 |

| Day | 11| 12| 13| 14| 15| 16| 17| 18| 19| 20 |
|-----|---|---|---|---|---|---|---|---|---|-----|
| Count | 19| 21| 17| 15| 23| 18| 20| 16| 19| 17 |

| Day | 21| 22| 23| 24| 25| 26| 27| 28| 29| 30 |
|-----|---|---|---|---|---|---|---|---|---|-----|
| Count | 21| 18| 16| 24| 19| 17| 20| 18| 22| 16 |

### Success Rate Trend
**Daily success rates (%) for each day of the month:**

| Day | 1-5 | 6-10 | 11-15 | 16-20 | 21-25 | 26-30 |
|-----|-----|------|-------|-------|-------|-------|
| Avg | 95% | 94%  | 95%   | 93%   | 95%   | 94%   |

### Storage Growth by Week
| Week | Storage (TB) |
|------|-------------|
| Week 1 | {{WEEK1_STORAGE}} |
| Week 2 | {{WEEK2_STORAGE}} |
| Week 3 | {{WEEK3_STORAGE}} |
| Week 4 | {{WEEK4_STORAGE}} |

### Retention Impact by Week
| Week | Snapshots Deleted |
|------|------------------|
| Week 1 | {{WEEK1_DELETED}} |
| Week 2 | {{WEEK2_DELETED}} |
| Week 3 | {{WEEK3_DELETED}} |
| Week 4 | {{WEEK4_DELETED}} |

---

## 👥 Client Performance Overview

{{CLIENT_PERFORMANCE_SUMMARY}}

### Client Performance Template:
```
### Client: [Client Name]
- **Total Snapshots:** X successful, Y failed
- **Storage Usage:** X GB
- **Success Rate:** X%
- **Key Issues:** [Any recurring problems]
- **Recommendations:** [Specific actions]
```

---

## 📋 Monthly Analysis & Recommendations

### Patterns Identified
{{MONTHLY_PATTERNS}}

#### Common Pattern Categories:
- **Day-of-week trends** (e.g., higher failure rates on Mondays)
- **Time-based patterns** (e.g., storage growth acceleration)
- **Client-specific behaviors** (e.g., seasonal backup variations)
- **System resource patterns** (e.g., peak usage periods)

### Recommendations
{{MONTHLY_RECOMMENDATIONS}}

#### Recommendation Categories:
- **Capacity Planning:** Storage and resource adjustments
- **Process Improvements:** Backup strategy optimization
- **Monitoring Enhancements:** Better alerting and visibility
- **Retention Policy Updates:** Policy adjustments based on usage

### Action Items for Next Month
{{NEXT_MONTH_ACTIONS}}

#### Action Item Template:
```
1. **[Priority]** [Action Description]
   - **Owner:** [Responsible Party]
   - **Due Date:** [Target Date]
   - **Success Criteria:** [How to measure completion]
```

---

## 📄 Complete Daily Details

### Daily Breakdown
{{COMPLETE_DAILY_DETAILS}}

#### Daily Detail Template:
```
### Day X - [Date]
**Overall Status:** [Status]
**Snapshots:** X successful, Y failed, Z deleted

#### Client Activity:
- **[Client 1]:** [Summary of activity]
- **[Client 2]:** [Summary of activity]

#### Notable Events:
- [Any significant events, failures, or maintenance]

#### Storage Impact:
- **Added:** X GB
- **Deleted:** Y GB  
- **Net Change:** Z GB
```

---

## 📊 Monthly Statistics

### Overall Metrics
- **Uptime:** {{MONTHLY_UPTIME}}%
- **Average Daily Snapshots:** {{AVG_DAILY_SNAPSHOTS}}
- **Peak Day Snapshots:** {{PEAK_DAY_SNAPSHOTS}}
- **Minimum Day Snapshots:** {{MIN_DAY_SNAPSHOTS}}

### Storage Metrics
- **Starting Month Storage:** {{START_MONTH_STORAGE}}
- **Ending Month Storage:** {{END_MONTH_STORAGE}}
- **Net Storage Growth:** {{NET_STORAGE_GROWTH}}
- **Average Daily Growth:** {{AVG_DAILY_GROWTH}}

### Retention Metrics
- **Total Snapshots Deleted:** {{TOTAL_MONTHLY_DELETIONS}}
- **Storage Space Reclaimed:** {{TOTAL_SPACE_RECLAIMED}}
- **Oldest Active Snapshot:** {{OLDEST_SNAPSHOT_DATE}}
- **Average Snapshot Age:** {{AVG_SNAPSHOT_AGE}}

---

**Report Generated:** {{GENERATION_TIMESTAMP}}  
**Comprehensive monthly backup analysis and retention tracking** 