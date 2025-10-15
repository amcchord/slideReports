# Setup Instructions for reports.slide.recipes

## Current Status

The Flask application has been configured and is ready to run. However, SSL certificates could not be generated because DNS is not configured yet.

## What's Done

- Flask application created with "Hello World" endpoint
- Virtual environment created and dependencies installed
- Apache HTTP configuration enabled and running
- Apache HTTPS configuration created (but disabled until certificates are ready)
- WSGI configuration set up to run Flask via Apache

## Next Steps to Complete SSL Setup

### 1. Configure DNS

Add an A record for `reports.slide.recipes` pointing to this server's IP address:

```
reports.slide.recipes    A    <server-ip-address>
```

Wait for DNS propagation (can take a few minutes to a few hours).

Verify DNS is working:
```bash
dig reports.slide.recipes
# or
nslookup reports.slide.recipes
```

### 2. Generate Let's Encrypt Certificates

Once DNS is configured and propagating, run:

```bash
sudo certbot --apache -d reports.slide.recipes
```

Certbot will:
- Validate domain ownership via HTTP challenge
- Generate SSL certificates
- Automatically update the Apache SSL configuration

### 3. Enable HTTPS Site

After certificates are generated:

```bash
sudo a2ensite reports.slide.recipes-le-ssl.conf
sudo systemctl reload apache2
```

### 4. Test the Site

HTTP (should redirect to HTTPS after SSL is set up):
```
http://reports.slide.recipes
```

HTTPS (after SSL certificates are installed):
```
https://reports.slide.recipes
```

## Current Access

While DNS is being configured, you can test the application locally:

```bash
cd /var/www/reports.slide.recipes
source venv/bin/activate
export FLASK_ENV=development
python app.py
```

This will run the app on `http://localhost:5000`

## Certificate Renewal

Let's Encrypt certificates expire after 90 days. Certbot sets up automatic renewal via systemd timer.

Check renewal status:
```bash
sudo certbot renew --dry-run
```

## Troubleshooting

### Check Apache logs
```bash
sudo tail -f /var/log/apache2/reports.slide.recipes-error.log
sudo tail -f /var/log/apache2/reports.slide.recipes-access.log
```

### Check Apache configuration
```bash
sudo apache2ctl configtest
```

### Restart Apache
```bash
sudo systemctl restart apache2
```

### Check if site is enabled
```bash
ls -la /etc/apache2/sites-enabled/ | grep reports
```

