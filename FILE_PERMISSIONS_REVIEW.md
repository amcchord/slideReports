# File System Permissions Security Review

**Date:** November 10, 2025  
**System:** reports.slide.recipes  
**Service Account:** www-data (Apache/WSGI)

## Current Configuration

### Service Account
- **Process User:** `www-data`
- **Process Group:** `www-data`
- **Parent Process:** Apache2 (running as root, spawns workers as www-data)

### Directory Permissions

| Directory/File | Owner | Group | Permissions | Status |
|----------------|-------|-------|-------------|--------|
| `/var/www/reports.slide.recipes/` | www-data | www-data | drwxr-xr-x (755) | ✅ Appropriate |
| `/var/www/reports.slide.recipes/data/` | www-data | www-data | drwxrwxr-x (775) | ⚠️ Too Permissive |
| `/var/www/reports.slide.recipes/lib/` | root | root | drwxr-xr-x (755) | ✅ Good |
| `/var/www/reports.slide.recipes/app.py` | www-data | www-data | -rw-r--r-- (644) | ✅ Good |
| `.env` file | root | root | -rw-r--r-- (644) | ⚠️ Should be 600 |

### Data Files
- **Database files (*.db):** www-data:www-data, 644 (rw-r--r--) ✅
- **Sync state (*.json):** www-data:www-data, 644 (rw-r--r--) ✅
- **Template databases:** www-data:www-data, 644 (rw-r--r--) ✅

## Security Analysis

### ✅ Current Strengths
1. **Least Privilege for Code:**
   - Application code (`app.py`, `lib/`) owned by root
   - www-data can read but not modify code
   - Prevents malicious code injection via web interface

2. **Appropriate Data Access:**
   - Data files owned by www-data for read/write
   - Database files have correct 644 permissions
   - Only www-data can write to data directory

3. **Process Isolation:**
   - Apache workers run as www-data (non-root)
   - Cannot modify system files
   - Limited to application directory

### ⚠️ Recommendations

#### Priority 1: Immediate Actions

1. **Restrict `.env` file permissions:**
   ```bash
   sudo chmod 600 /var/www/reports.slide.recipes/.env
   ```
   - Contains sensitive configuration
   - Should only be readable by root

2. **Tighten data directory permissions:**
   ```bash
   sudo chmod 770 /var/www/reports.slide.recipes/data
   ```
   - Current 775 allows "others" to read/execute
   - Should be restricted to owner and group only

#### Priority 2: Enhanced Security

3. **Create dedicated service account:**
   ```bash
   sudo useradd -r -s /bin/false -d /var/www/reports.slide.recipes slide-reports
   sudo chown -R slide-reports:www-data /var/www/reports.slide.recipes
   ```
   - Separate from generic www-data
   - Limits impact if other web apps are compromised

4. **Implement AppArmor/SELinux profile:**
   - Restrict which files the application can access
   - Prevent access to `/etc/passwd`, `/etc/shadow`, etc.
   - Limit network access to required ports only

5. **Add file integrity monitoring:**
   ```bash
   # Monitor for unauthorized changes to application code
   sudo apt-get install aide
   ```

#### Priority 3: Defense in Depth

6. **Restrict log file access:**
   - Ensure application logs are only readable by www-data and root
   - Rotate logs regularly
   - Consider shipping logs to centralized logging

7. **Database file encryption:**
   - Consider encrypting SQLite database files at rest
   - Use LUKS or similar for volume encryption

8. **Backup permissions:**
   - Ensure backup files have restricted permissions
   - Store backups in separate location
   - Encrypt backup data

## Current Risk Assessment

| Risk Factor | Level | Mitigation |
|-------------|-------|------------|
| **Code Injection** | LOW | ✅ Code files owned by root |
| **Data Access** | LOW | ✅ Data files restricted to www-data |
| **Privilege Escalation** | LOW | ✅ Running as non-root user |
| **Information Disclosure** | MEDIUM | ⚠️ .env file too permissive |
| **Lateral Movement** | MEDIUM | ⚠️ Using generic www-data account |

## Implementation Commands

### Immediate Hardening (Run these now)

```bash
# 1. Restrict .env file
sudo chmod 600 /var/www/reports.slide.recipes/.env
sudo chown root:root /var/www/reports.slide.recipes/.env

# 2. Tighten data directory
sudo chmod 770 /var/www/reports.slide.recipes/data

# 3. Verify library permissions
sudo chown -R root:root /var/www/reports.slide.recipes/lib
sudo chmod 755 /var/www/reports.slide.recipes/lib
sudo find /var/www/reports.slide.recipes/lib -type f -exec chmod 644 {} \;

# 4. Verify Python cache permissions
sudo chown -R www-data:www-data /var/www/reports.slide.recipes/__pycache__
sudo chmod 755 /var/www/reports.slide.recipes/__pycache__

# 5. Verify venv permissions (if used)
if [ -d "/var/www/reports.slide.recipes/venv" ]; then
    sudo chown -R root:root /var/www/reports.slide.recipes/venv
    sudo chmod 755 /var/www/reports.slide.recipes/venv
fi
```

### Optional: Create Dedicated Service Account

```bash
# Create dedicated service account
sudo useradd -r -s /bin/false -d /var/www/reports.slide.recipes slide-reports
sudo usermod -a -G slide-reports www-data

# Update ownership
sudo chown -R slide-reports:slide-reports /var/www/reports.slide.recipes
sudo chown -R root:root /var/www/reports.slide.recipes/lib

# Update Apache configuration
# Edit: /etc/apache2/sites-available/reports.slide.recipes.conf
# Add: WSGIDaemonProcess reports user=slide-reports group=slide-reports
```

## Monitoring Recommendations

### File Integrity Monitoring
```bash
# Daily check for unauthorized modifications
find /var/www/reports.slide.recipes -type f -name "*.py" -mtime -1

# Alert on permission changes
find /var/www/reports.slide.recipes -perm /002 -ls
```

### Access Monitoring
```bash
# Monitor for suspicious file access
sudo ausearch -f /var/www/reports.slide.recipes/data -ts recent

# Check for unauthorized users
getent group www-data
```

## Compliance Notes

- **CIS Benchmark:** Meets most web server hardening requirements
- **OWASP:** Follows least privilege principles
- **PCI-DSS:** Appropriate for systems handling sensitive data

## Conclusion

The current file permission configuration is **generally secure** with the following caveats:

✅ **Strengths:**
- Application code protected (owned by root)
- Non-root execution (www-data)
- Data files appropriately restricted

⚠️ **Improvements Needed:**
- Restrict .env file permissions immediately
- Tighten data directory permissions
- Consider dedicated service account

🔒 **Post-Hardening Risk Level:** LOW (from MEDIUM)

---

**Review Status:** COMPLETE  
**Action Required:** Implement Priority 1 recommendations immediately

