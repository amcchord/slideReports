# Quick Start Guide

## Starting the Application

### Development Mode

```bash
cd /var/www/reports.slide.recipes
source venv/bin/activate
python app.py
```

Access at: http://localhost:5000

### Production Mode (with Gunicorn)

```bash
cd /var/www/reports.slide.recipes
source venv/bin/activate
gunicorn -w 4 -b 0.0.0.0:5000 wsgi:app
```

## First Time Setup

1. **Access the application** in your browser
2. **Enter Slide API key**: `tk_hlr3e2d2e7x1_kUqKky4bb3zfefnkKlI8h4GbsNeC8Rx6`
3. **Dashboard loads** - you'll see the main interface

## Quick Workflow

### 1. Sync Data (First Time)

1. Click "Sync Now" on dashboard
2. Wait for progress indicators to complete
3. All data sources will be fetched from Slide API

### 2. Create a Report

**Option A: Use Default Template**
1. Go to "Build Report"
2. Select template: "Default Professional Template"
3. Choose date range (default: last 30 days)
4. Click "Preview Report"
5. Click "Print / Save as PDF"

**Option B: Create Custom Template with AI**
1. Go to "Templates" → "Create New Template"
2. Enter description, e.g.:
   ```
   Create a backup report with a green header, showing backup 
   success rates, storage usage bars, and a list of recent alerts
   ```
3. Click "Generate Template with AI"
4. Save template
5. Use in report builder

## Environment Variables

The application needs these to run:

```bash
export ENCRYPTION_KEY=a7b3c5d9e1f2a4b6c8d0e2f4a6b8c0d2
export CLAUDE_API_KEY=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
export FLASK_SECRET_KEY=slide-reports-production-secret-key-2025
export FLASK_ENV=production
export DATA_DIR=/var/www/reports.slide.recipes/data
```

## Testing

Run basic functionality tests:

```bash
cd /var/www/reports.slide.recipes
source venv/bin/activate
export ENCRYPTION_KEY=a7b3c5d9e1f2a4b6c8d0e2f4a6b8c0d2
export TEST_SLIDE_API_KEY=tk_hlr3e2d2e7x1_kUqKky4bb3zfefnkKlI8h4GbsNeC8Rx6
python test_basic.py
```

## Troubleshooting

### App won't start

1. Check virtual environment is activated: `source venv/bin/activate`
2. Check dependencies installed: `pip install -r requirements.txt`
3. Check environment variables are set
4. Check port 5000 is available

### Can't connect to Slide API

1. Verify API key is valid
2. Check internet connectivity
3. Review Slide API status

### Template generation fails

1. Verify CLAUDE_API_KEY is set correctly
2. Check Claude API quota/limits
3. Try simpler description

## Default Login

There is no login - authentication is handled via encrypted API key cookie.
First time visitors will see the setup page to enter their Slide API key.

## Data Location

- Databases: `/var/www/reports.slide.recipes/data/`
- Each user: `{api_key_hash}.db` and `{api_key_hash}_templates.db`
- Logs: Check console output or configure logging

## Production Deployment

For production, consider:

1. Use systemd service or supervisor to manage gunicorn
2. Use nginx as reverse proxy
3. Enable HTTPS/SSL
4. Set FLASK_ENV=production
5. Rotate logs
6. Monitor disk space in data directory
7. Backup databases regularly

## Support

- README.md - Full documentation
- Slide Docs: https://docs.slide.tech
- API Reference: docs/slideAPI.json

