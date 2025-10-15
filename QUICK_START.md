# Quick Start Guide - reports.slide.recipes

## Activate Virtual Environment

```bash
cd /var/www/reports.slide.recipes
source venv/bin/activate
```

Or use the helper script:
```bash
source /var/www/reports.slide.recipes/activate_venv.sh
```

## Run Locally (Development)

```bash
cd /var/www/reports.slide.recipes
source venv/bin/activate
export FLASK_ENV=development
python app.py
```

Access at: `http://localhost:5000`

## Complete SSL Setup (After DNS is configured)

### Step 1: Verify DNS
```bash
dig reports.slide.recipes
```

### Step 2: Generate Certificates
```bash
sudo certbot --apache -d reports.slide.recipes
```

### Step 3: Enable HTTPS Site
```bash
sudo a2ensite reports.slide.recipes-le-ssl.conf
sudo systemctl reload apache2
```

## Common Apache Commands

```bash
# Restart Apache
sudo systemctl restart apache2

# Reload Apache (graceful)
sudo systemctl reload apache2

# Test configuration
sudo apache2ctl configtest

# View enabled sites
ls -la /etc/apache2/sites-enabled/
```

## View Logs

```bash
# Error log
sudo tail -f /var/log/apache2/reports.slide.recipes-error.log

# Access log
sudo tail -f /var/log/apache2/reports.slide.recipes-access.log
```

## Endpoints

- `/` - Hello World
- `/health` - Health check (JSON)

## Files Reference

- **App**: `/var/www/reports.slide.recipes/app.py`
- **WSGI**: `/var/www/reports.slide.recipes/wsgi.py`
- **HTTP Config**: `/etc/apache2/sites-available/reports.slide.recipes.conf`
- **HTTPS Config**: `/etc/apache2/sites-available/reports.slide.recipes-le-ssl.conf`
- **Venv**: `/var/www/reports.slide.recipes/venv/`

## Current Status

✅ Flask app created and working
✅ Apache HTTP site enabled
✅ Virtual environment set up
⏳ DNS not configured yet
⏳ SSL certificates not generated yet

## Next Step

**Configure DNS A record for reports.slide.recipes pointing to this server's IP address**

