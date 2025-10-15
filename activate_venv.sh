#!/bin/bash
# Quick script to activate the virtual environment

cd /var/www/reports.slide.recipes
source venv/bin/activate

echo "Virtual environment activated!"
echo "Project directory: /var/www/reports.slide.recipes"
echo ""
echo "Quick commands:"
echo "  python app.py              - Run Flask app locally"
echo "  pip install -r requirements.txt  - Install/update dependencies"
echo "  deactivate                 - Exit virtual environment"
echo ""
echo "Apache commands (requires sudo):"
echo "  sudo systemctl restart apache2  - Restart Apache"
echo "  sudo tail -f /var/log/apache2/reports.slide.recipes-error.log  - View error logs"
echo ""

