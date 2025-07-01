# {{Client}} Disaster Recovery Runbook

> **CONFIDENTIAL** - For Authorized Personnel Only  
> Emergency Response and System Recovery Procedures

---

## LLM Instructions

**IMPORTANT:** When filling this template, replace the entire `{{PLACEHOLDER}}` with just your content.

**Examples:**
- ❌ Wrong: `{{SYSTEM_NAME}}` → `{{My Production System}}`
- ✅ Correct: `{{SYSTEM_NAME}}` → `My Production System`

**When done:** Remove this entire instruction section and all placeholder references.

---

## Document Information

| Field | Value |
|-------|-------|
| **System/Service Name** | {{SYSTEM_NAME}} |
| **Document Version** | {{DOCUMENT_VERSION}} |
| **Last Updated** | {{LAST_UPDATED_DATE}} |
| **Next Review Date** | {{NEXT_REVIEW_DATE}} |

---

## 🚨 Emergency Contacts

### Primary On-Call Engineer
- **Name:** {{PRIMARY_ONCALL_NAME}}
- **Phone:** {{PRIMARY_ONCALL_PHONE}}
- **Email:** {{PRIMARY_ONCALL_EMAIL}}

### Secondary On-Call Engineer
- **Name:** {{SECONDARY_ONCALL_NAME}}
- **Phone:** {{SECONDARY_ONCALL_PHONE}}
- **Email:** {{SECONDARY_ONCALL_EMAIL}}

### Management Contact
- **Name:** {{MANAGER_NAME}}
- **Phone:** {{MANAGER_PHONE}}
- **Email:** {{MANAGER_EMAIL}}

---

## System Overview

### System Description
{{SYSTEM_DESCRIPTION}}

### Business Impact
{{BUSINESS_IMPACT}}

### Recovery Time Objective (RTO)
{{RTO}}

### Recovery Point Objective (RPO)
{{RPO}}

---

## Server Infrastructure

### 🟢 Primary Servers (Bring up FIRST)

#### Server 1 - Critical
| Field | Value |
|-------|-------|
| **Hostname** | {{PRIMARY_SERVER1_HOSTNAME}} |
| **IP Address** | {{PRIMARY_SERVER1_IP}} |
| **Role/Function** | {{PRIMARY_SERVER1_ROLE}} |
| **OS/Version** | {{PRIMARY_SERVER1_OS}} |
| **Hardware Specs** | {{PRIMARY_SERVER1_SPECS}} |
| **Location** | {{PRIMARY_SERVER1_LOCATION}} |

**Key Services:**
{{PRIMARY_SERVER1_SERVICES}}

**Dependencies:**
{{PRIMARY_SERVER1_DEPENDENCIES}}

#### Additional Primary Servers
{{ADDITIONAL_PRIMARY_SERVERS}}

### 🟡 Secondary Servers (Bring up SECOND)

#### Server 2 - Important
| Field | Value |
|-------|-------|
| **Hostname** | {{SECONDARY_SERVER1_HOSTNAME}} |
| **IP Address** | {{SECONDARY_SERVER1_IP}} |
| **Role/Function** | {{SECONDARY_SERVER1_ROLE}} |
| **OS/Version** | {{SECONDARY_SERVER1_OS}} |
| **Hardware Specs** | {{SECONDARY_SERVER1_SPECS}} |
| **Location** | {{SECONDARY_SERVER1_LOCATION}} |

**Key Services:**
{{SECONDARY_SERVER1_SERVICES}}

**Dependencies:**
{{SECONDARY_SERVER1_DEPENDENCIES}}

#### Additional Secondary Servers
{{ADDITIONAL_SECONDARY_SERVERS}}

### ⚪ Optional Servers (Bring up LAST)

#### Server 3 - Optional
| Field | Value |
|-------|-------|
| **Hostname** | {{OPTIONAL_SERVER1_HOSTNAME}} |
| **IP Address** | {{OPTIONAL_SERVER1_IP}} |
| **Role/Function** | {{OPTIONAL_SERVER1_ROLE}} |
| **OS/Version** | {{OPTIONAL_SERVER1_OS}} |
| **Hardware Specs** | {{OPTIONAL_SERVER1_SPECS}} |
| **Location** | {{OPTIONAL_SERVER1_LOCATION}} |

**Key Services:**
{{OPTIONAL_SERVER1_SERVICES}}

**Dependencies:**
{{OPTIONAL_SERVER1_DEPENDENCIES}}

#### Additional Optional Servers
{{ADDITIONAL_OPTIONAL_SERVERS}}

---

## Network Configuration

### Network Segments
- **Production Network:** {{PROD_NETWORK_RANGE}}
- **Management Network:** {{MGMT_NETWORK_RANGE}}
- **DMZ Network:** {{DMZ_NETWORK_RANGE}}

### Key Network Devices
- **Primary Router:** {{PRIMARY_ROUTER_IP}}
- **Core Switch:** {{CORE_SWITCH_IP}}
- **Firewall:** {{FIREWALL_IP}}

### DNS Configuration
- **Primary DNS:** {{PRIMARY_DNS}}
- **Secondary DNS:** {{SECONDARY_DNS}}
- **Domain:** {{DOMAIN_NAME}}

### Load Balancers / VIPs
{{LOAD_BALANCER_CONFIG}}

### External Dependencies
{{EXTERNAL_DEPENDENCIES}}

---

## 🚨 Recovery Procedures

### Step 1: Initial Assessment

#### Incident Assessment Checklist
{{INCIDENT_ASSESSMENT_STEPS}}

#### Communication Protocol
{{COMMUNICATION_PROTOCOL}}

### Step 2: Network Recovery
{{NETWORK_RECOVERY_STEPS}}

### Step 3: Primary Server Recovery
{{PRIMARY_SERVER_RECOVERY_STEPS}}

### Step 4: Secondary Server Recovery
{{SECONDARY_SERVER_RECOVERY_STEPS}}

### Step 5: Service Validation
{{SERVICE_VALIDATION_STEPS}}

### Step 6: Data Integrity Verification
{{DATA_INTEGRITY_VERIFICATION}}

---

## Recovery Commands & Scripts

### Common Recovery Commands
```bash
{{RECOVERY_COMMANDS}}
```

### Key File Locations
{{KEY_FILE_LOCATIONS}}

### Backup Locations
{{BACKUP_LOCATIONS}}

### Service Start/Stop Commands
```bash
{{SERVICE_COMMANDS}}
```

---

## ✅ Testing and Validation

### System Health Checks
{{SYSTEM_HEALTH_CHECKS}}

### Application Testing
{{APPLICATION_TESTING_STEPS}}

### Performance Validation
{{PERFORMANCE_VALIDATION}}

### User Acceptance Testing
{{USER_ACCEPTANCE_TESTING}}

---

## 📋 Post-Recovery Actions

### Documentation Updates
{{DOCUMENTATION_UPDATES}}

### Lessons Learned
{{LESSONS_LEARNED}}

### Process Improvements
{{PROCESS_IMPROVEMENTS}}

### Stakeholder Communication
{{STAKEHOLDER_COMMUNICATION}}

---

## 📚 Additional Resources

### Documentation Links
{{DOCUMENTATION_LINKS}}

### Vendor Support Contacts
{{VENDOR_SUPPORT_CONTACTS}}

### Monitoring Tools
{{MONITORING_TOOLS}}

### Escalation Procedures
{{ESCALATION_PROCEDURES}}

---

## Document Footer

**© 2024 Disaster Recovery Runbook | Confidential Document**

*This document contains sensitive information. Handle according to company security policies.* 