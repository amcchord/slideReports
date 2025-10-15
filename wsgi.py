#!/usr/bin/env python3
import sys
import os
from dotenv import load_dotenv

# Add the project directory to the Python path
sys.path.insert(0, "/var/www/reports.slide.recipes/")

# Explicitly load .env file with absolute path for Apache/mod_wsgi
load_dotenv("/var/www/reports.slide.recipes/.env")

from app import app, auto_sync_scheduler, logger

# Start auto-sync scheduler for WSGI/production
try:
    auto_sync_scheduler.start()
    logger.info("Auto-sync scheduler initialized in WSGI mode")
except Exception as e:
    logger.error(f"Failed to start auto-sync scheduler in WSGI: {e}")

# WSGI expects an 'application' variable
application = app

if __name__ == "__main__":
    app.run()

