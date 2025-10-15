# Reports - Slide Recipes

Flask application for reports.slide.recipes

## Setup Instructions

### 1. Environment Setup

Copy the example environment file and configure as needed:

```bash
cp .env.example .env
```

### 2. Virtual Environment

The application uses a Python virtual environment located in the `venv/` directory.

#### Activate the virtual environment:

```bash
source venv/bin/activate
```

#### Deactivate when done:

```bash
deactivate
```

### 3. Install Dependencies

With the virtual environment activated:

```bash
pip install -r requirements.txt
```

### 4. Running Locally (Development)

```bash
source venv/bin/activate
export FLASK_ENV=development
python app.py
```

The app will be available at `http://localhost:5000`

### 5. Production Deployment

The application is configured to run via Apache with mod_wsgi. The configuration files are located at:

- `/etc/apache2/sites-available/reports.slide.recipes.conf` (HTTP)
- `/etc/apache2/sites-available/reports.slide.recipes-le-ssl.conf` (HTTPS)

#### Restart Apache after changes:

```bash
sudo systemctl restart apache2
```

#### Check Apache logs:

```bash
sudo tail -f /var/log/apache2/reports.slide.recipes-error.log
sudo tail -f /var/log/apache2/reports.slide.recipes-access.log
```

## Project Structure

```
/var/www/reports.slide.recipes/
├── app.py              # Flask application
├── wsgi.py             # WSGI entry point for Apache
├── requirements.txt    # Python dependencies
├── .env                # Environment configuration (not in git)
├── .env.example        # Example environment configuration
├── venv/               # Python virtual environment
├── static/             # Static files (CSS, JS, images)
└── templates/          # HTML templates
```

## Quick Commands

```bash
# Activate environment
source venv/bin/activate

# Update dependencies
pip install -r requirements.txt

# Check Apache config
sudo apache2ctl configtest

# Restart Apache
sudo systemctl restart apache2

# View logs
sudo tail -f /var/log/apache2/reports.slide.recipes-error.log
```

