"""
Slide Reports System - Main Flask Application
"""
import os
import logging
from datetime import datetime, timedelta
from flask import Flask, render_template, request, jsonify, redirect, url_for, make_response
from dotenv import load_dotenv

from lib.encryption import Encryption
from lib.database import Database, get_database_path
from lib.slide_api import SlideAPIClient
from lib.sync import SyncEngine
from lib.templates import TemplateManager
from lib.ai_generator import AITemplateGenerator
from lib.report_generator import ReportGenerator
from lib.background_sync import background_sync
from lib.scheduler import auto_sync_scheduler

# Application version
VERSION = "1.0.0"

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'dev-secret-key-change-in-production')

# Initialize encryption
encryption_key = os.environ.get('ENCRYPTION_KEY')
if not encryption_key:
    raise ValueError("ENCRYPTION_KEY environment variable must be set")
encryption = Encryption(encryption_key)

# Initialize AI generator
claude_api_key = os.environ.get('CLAUDE_API_KEY')
if not claude_api_key:
    raise ValueError("CLAUDE_API_KEY environment variable must be set")
ai_generator = AITemplateGenerator(claude_api_key)


# Helper Functions
def get_api_key_from_cookie() -> tuple[str | None, str | None]:
    """
    Get and decrypt API key from cookie.
    
    Returns:
        Tuple of (api_key, api_key_hash) or (None, None) if not found
    """
    encrypted_key = request.cookies.get('slide_api_key')
    if not encrypted_key:
        return None, None
    
    try:
        api_key = encryption.decrypt(encrypted_key)
        api_key_hash = Encryption.hash_api_key(api_key)
        return api_key, api_key_hash
    except Exception as e:
        logger.error(f"Failed to decrypt API key: {e}")
        return None, None


def require_api_key(f):
    """Decorator to require valid API key"""
    from functools import wraps
    
    @wraps(f)
    def decorated_function(*args, **kwargs):
        api_key, api_key_hash = get_api_key_from_cookie()
        if not api_key:
            if request.is_json:
                return jsonify({'error': 'API key required'}), 401
            return redirect(url_for('setup'))
        return f(api_key, api_key_hash, *args, **kwargs)
    return decorated_function


# Routes
@app.route('/')
def index():
    """Home page - redirect to dashboard or setup"""
    api_key, _ = get_api_key_from_cookie()
    if api_key:
        return redirect(url_for('dashboard'))
    return redirect(url_for('setup'))


@app.route('/setup')
def setup():
    """API key setup page"""
    return render_template('setup.html')


@app.route('/api/setup', methods=['POST'])
def api_setup():
    """Save encrypted API key cookie"""
    data = request.get_json()
    api_key = data.get('api_key', '').strip()
    
    if not Encryption.validate_api_key_format(api_key):
        return jsonify({'error': 'Invalid API key format'}), 400
    
    # Test API key
    try:
        client = SlideAPIClient(api_key)
        if not client.test_connection():
            return jsonify({'error': 'API key is invalid or unauthorized'}), 401
    except Exception as e:
        logger.error(f"API test failed: {e}")
        return jsonify({'error': 'Failed to validate API key'}), 500
    
    # Encrypt and set cookie
    encrypted_key = encryption.encrypt(api_key)
    
    response = jsonify({'success': True})
    response.set_cookie(
        'slide_api_key',
        encrypted_key,
        max_age=30*24*60*60,  # 30 days
        httponly=True,
        secure=request.is_secure,
        samesite='Lax'
    )
    
    return response


@app.route('/dashboard')
@require_api_key
def dashboard(api_key, api_key_hash):
    """Main dashboard"""
    from datetime import datetime
    import pytz
    from lib.report_generator import format_datetime_friendly
    
    db = Database(get_database_path(api_key_hash))
    
    # Get sync status
    sync_engine = SyncEngine(SlideAPIClient(api_key), db)
    sync_status = sync_engine.get_sync_status()
    
    # Get background sync state
    bg_state = background_sync.get_sync_state(api_key_hash)
    
    # Get data counts
    counts = db.get_data_source_counts()
    
    # Get timezone
    timezone = db.get_preference('timezone', 'America/New_York')
    user_tz = pytz.timezone(timezone)
    
    # Add friendly date formatting to sync status
    for key, status in sync_status.items():
        if status.get('last_sync'):
            try:
                last_sync_dt = datetime.fromisoformat(status['last_sync'].replace('Z', '+00:00'))
                status['last_sync_friendly'] = format_datetime_friendly(last_sync_dt, user_tz)
            except Exception:
                status['last_sync_friendly'] = 'Unknown'
        else:
            status['last_sync_friendly'] = 'Never'
    
    return render_template('dashboard.html',
                         sync_status=sync_status,
                         counts=counts,
                         timezone=timezone,
                         is_syncing=bg_state.get('status') == 'syncing')


@app.route('/api/sync', methods=['POST'])
@require_api_key
def api_sync(api_key, api_key_hash):
    """Trigger data sync in background"""
    data = request.get_json() or {}
    data_sources = data.get('data_sources', None)
    
    # Start background sync
    started = background_sync.start_sync(api_key, api_key_hash, data_sources)
    
    if not started:
        return jsonify({'error': 'Sync already in progress'}), 409
    
    return jsonify({'status': 'started', 'message': 'Sync started in background'}), 202


@app.route('/api/sync/status')
@require_api_key
def api_sync_status(api_key, api_key_hash):
    """Get current sync status (real-time during sync)"""
    # Get background sync state
    bg_state = background_sync.get_sync_state(api_key_hash)
    
    # Get database sync status
    db = Database(get_database_path(api_key_hash))
    client = SlideAPIClient(api_key)
    sync_engine = SyncEngine(client, db)
    db_status = sync_engine.get_sync_status()
    
    # If syncing, merge with real-time progress
    if bg_state.get('status') == 'syncing':
        for source, progress_data in bg_state.get('progress', {}).items():
            if source in db_status:
                db_status[source]['status'] = 'syncing'
                db_status[source]['current_items'] = progress_data.get('current', 0)
                db_status[source]['total_items_fetching'] = progress_data.get('total', 0)
    
    # Add overall sync state
    response = {
        'sources': db_status,
        'sync_state': bg_state.get('status', 'idle'),
        'current_source': bg_state.get('current_source')
    }
    
    return jsonify(response)


@app.route('/api/data/sources')
@require_api_key
def api_data_sources(api_key, api_key_hash):
    """Get available data sources with counts"""
    db = Database(get_database_path(api_key_hash))
    counts = db.get_data_source_counts()
    
    sources = []
    for key, name in SyncEngine.DATA_SOURCES.items():
        sources.append({
            'key': key,
            'name': name,
            'count': counts.get(key, 0)
        })
    
    return jsonify(sources)


@app.route('/api/clients')
@require_api_key
def api_clients(api_key, api_key_hash):
    """Get list of clients"""
    db = Database(get_database_path(api_key_hash))
    clients = db.get_records('clients', order_by='name')
    
    return jsonify(clients)


@app.route('/templates')
@require_api_key
def templates_list(api_key, api_key_hash):
    """List all templates"""
    tm = TemplateManager(api_key_hash)
    templates = tm.list_templates()
    
    return render_template('templates_list.html', templates=templates)


@app.route('/templates/new')
@require_api_key
def templates_new(api_key, api_key_hash):
    """Create new template page"""
    tm = TemplateManager(api_key_hash)
    default_template = tm.get_default_template()
    
    # Get data sources
    db = Database(get_database_path(api_key_hash))
    counts = db.get_data_source_counts()
    
    data_sources = []
    for key, name in SyncEngine.DATA_SOURCES.items():
        data_sources.append({
            'key': key,
            'name': name,
            'count': counts.get(key, 0)
        })
    
    return render_template('template_editor.html',
                         template=None,
                         default_description='Create a professional backup report with charts and statistics',
                         data_sources=data_sources)


@app.route('/templates/<int:template_id>')
@require_api_key
def templates_view(api_key, api_key_hash, template_id):
    """View/edit template"""
    tm = TemplateManager(api_key_hash)
    template = tm.get_template(template_id)
    
    if not template:
        return "Template not found", 404
    
    # Get data sources
    db = Database(get_database_path(api_key_hash))
    counts = db.get_data_source_counts()
    
    data_sources = []
    for key, name in SyncEngine.DATA_SOURCES.items():
        data_sources.append({
            'key': key,
            'name': name,
            'count': counts.get(key, 0)
        })
    
    return render_template('template_editor.html',
                         template=template,
                         data_sources=data_sources)


@app.route('/api/templates', methods=['POST'])
@require_api_key
def api_templates_create(api_key, api_key_hash):
    """Create new template"""
    data = request.get_json()
    name = data.get('name')
    description = data.get('description', '')
    html_content = data.get('html_content')
    
    if not name or not html_content:
        return jsonify({'error': 'Name and HTML content required'}), 400
    
    tm = TemplateManager(api_key_hash)
    template_id = tm.create_template(name, description, html_content)
    
    return jsonify({'template_id': template_id, 'success': True}), 201


@app.route('/api/templates/<int:template_id>', methods=['PATCH'])
@require_api_key
def api_templates_update(api_key, api_key_hash, template_id):
    """Update template"""
    data = request.get_json()
    
    tm = TemplateManager(api_key_hash)
    tm.update_template(
        template_id,
        name=data.get('name'),
        description=data.get('description'),
        html_content=data.get('html_content')
    )
    
    return jsonify({'success': True})


@app.route('/api/templates/<int:template_id>', methods=['DELETE'])
@require_api_key
def api_templates_delete(api_key, api_key_hash, template_id):
    """Delete template"""
    tm = TemplateManager(api_key_hash)
    tm.delete_template(template_id)
    
    return '', 204


@app.route('/api/templates/generate', methods=['POST'])
@require_api_key
def api_templates_generate(api_key, api_key_hash):
    """Generate template with AI"""
    data = request.get_json()
    description = data.get('description')
    data_sources = data.get('data_sources', [])
    
    if not description:
        return jsonify({'error': 'Description required'}), 400
    
    try:
        html = ai_generator.generate_template(description, data_sources)
        return jsonify({'html': html})
    except Exception as e:
        logger.error(f"Template generation failed: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/reports/builder')
@require_api_key
def reports_builder(api_key, api_key_hash):
    """Report builder interface"""
    tm = TemplateManager(api_key_hash)
    templates = tm.list_templates()
    
    db = Database(get_database_path(api_key_hash))
    counts = db.get_data_source_counts()
    timezone = db.get_preference('timezone', 'America/New_York')
    
    data_sources = []
    for key, name in SyncEngine.DATA_SOURCES.items():
        data_sources.append({
            'key': key,
            'name': name,
            'count': counts.get(key, 0)
        })
    
    # Get list of clients for filtering
    clients = db.get_records('clients', order_by='name')
    
    return render_template('report_builder.html',
                         templates=templates,
                         data_sources=data_sources,
                         clients=clients,
                         timezone=timezone)


@app.route('/api/reports/preview', methods=['POST'])
@require_api_key
def api_reports_preview(api_key, api_key_hash):
    """Generate report preview"""
    data = request.get_json()
    template_id = data.get('template_id')
    start_date_str = data.get('start_date')
    end_date_str = data.get('end_date')
    data_sources = data.get('data_sources', [])
    client_id = data.get('client_id')  # Optional client filter
    
    # Parse dates
    start_date = datetime.fromisoformat(start_date_str) if start_date_str else None
    end_date = datetime.fromisoformat(end_date_str) if end_date_str else None
    
    # Get template
    tm = TemplateManager(api_key_hash)
    template = tm.get_template(template_id)
    
    if not template:
        return jsonify({'error': 'Template not found'}), 404
    
    # Generate report
    db = Database(get_database_path(api_key_hash))
    generator = ReportGenerator(db)
    
    try:
        html = generator.generate_report(
            template['html_content'],
            start_date,
            end_date,
            data_sources,
            logo_url='/static/img/logo.png',
            client_id=client_id,
            ai_generator=ai_generator
        )
        return jsonify({'html': html})
    except Exception as e:
        logger.error(f"Report generation failed: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/preferences/timezone', methods=['POST'])
@require_api_key
def api_set_timezone(api_key, api_key_hash):
    """Set user timezone preference"""
    data = request.get_json()
    timezone = data.get('timezone')
    
    if not timezone:
        return jsonify({'error': 'Timezone required'}), 400
    
    db = Database(get_database_path(api_key_hash))
    db.set_preference('timezone', timezone)
    
    return jsonify({'success': True})


@app.route('/report-values')
@require_api_key
def report_values_docs(api_key, api_key_hash):
    """Documentation page for all available report template variables"""
    return render_template('report_values.html')


@app.route('/logout')
def logout():
    """Clear API key cookie"""
    response = redirect(url_for('setup'))
    response.set_cookie('slide_api_key', '', max_age=0)
    return response


@app.route('/api/preferences/auto-sync', methods=['POST'])
@require_api_key
def api_set_auto_sync(api_key, api_key_hash):
    """Toggle auto-sync preference"""
    data = request.get_json()
    enabled = data.get('enabled', True)
    
    db = Database(get_database_path(api_key_hash))
    db.set_preference('auto_sync_enabled', 'true' if enabled else 'false')
    
    return jsonify({'success': True, 'enabled': enabled})


@app.route('/api/sync/next')
@require_api_key
def api_sync_next(api_key, api_key_hash):
    """Get next scheduled sync time"""
    db = Database(get_database_path(api_key_hash))
    auto_sync_enabled = db.get_preference('auto_sync_enabled', 'true').lower() == 'true'
    frequency_hours = int(db.get_preference('auto_sync_frequency_hours', '1'))
    
    # Get last sync time
    bg_state = background_sync.get_sync_state(api_key_hash)
    last_sync = bg_state.get('completed_at')
    
    next_sync = None
    if auto_sync_enabled and last_sync:
        from datetime import datetime, timedelta
        last_sync_dt = datetime.fromisoformat(last_sync)
        next_sync_dt = last_sync_dt + timedelta(hours=frequency_hours)
        next_sync = next_sync_dt.isoformat()
    
    return jsonify({
        'auto_sync_enabled': auto_sync_enabled,
        'frequency_hours': frequency_hours,
        'last_sync': last_sync,
        'next_sync': next_sync
    })


@app.route('/health')
def health_check():
    """Health check endpoint"""
    return jsonify({'status': 'healthy', 'version': VERSION})


# Admin Routes
def require_admin_auth(f):
    """Decorator to require admin authentication"""
    def wrapper(*args, **kwargs):
        admin_pass = os.environ.get('ADMIN_PASS')
        if not admin_pass:
            return jsonify({'error': 'Admin functionality not configured'}), 503
        
        auth_header = request.headers.get('Authorization')
        if not auth_header or auth_header != f'Bearer {admin_pass}':
            return jsonify({'error': 'Unauthorized'}), 401
        
        return f(*args, **kwargs)
    wrapper.__name__ = f.__name__
    return wrapper


@app.route('/admin')
def admin_page():
    """Admin dashboard page"""
    admin_pass = os.environ.get('ADMIN_PASS')
    if not admin_pass:
        return render_template('error.html', error='Admin functionality not configured'), 503
    
    # Check if authorized via session or show login
    auth_token = request.cookies.get('admin_auth')
    if auth_token != admin_pass:
        # Show simple login page
        return render_template('admin_login.html')
    
    from lib.admin_utils import list_all_api_keys, get_system_stats, format_bytes
    
    api_keys = list_all_api_keys()
    stats = get_system_stats()
    
    return render_template('admin.html', 
                         api_keys=api_keys, 
                         stats=stats,
                         format_bytes=format_bytes)


@app.route('/admin/auth', methods=['POST'])
def admin_auth():
    """Authenticate admin"""
    admin_pass = os.environ.get('ADMIN_PASS')
    if not admin_pass:
        return jsonify({'error': 'Admin functionality not configured'}), 503
    
    data = request.get_json()
    password = data.get('password')
    
    if password == admin_pass:
        response = jsonify({'success': True})
        response.set_cookie('admin_auth', admin_pass, max_age=86400)  # 24 hours
        return response
    
    return jsonify({'error': 'Invalid password'}), 401


@app.route('/admin/api/keys/<api_key_hash>/auto-sync', methods=['POST'])
def admin_toggle_auto_sync(api_key_hash):
    """Toggle auto-sync for a specific API key"""
    admin_pass = os.environ.get('ADMIN_PASS')
    auth_token = request.cookies.get('admin_auth')
    
    if not admin_pass or auth_token != admin_pass:
        return jsonify({'error': 'Unauthorized'}), 401
    
    from lib.admin_utils import toggle_auto_sync
    
    data = request.get_json()
    enabled = data.get('enabled', True)
    
    success = toggle_auto_sync(api_key_hash, enabled)
    
    if success:
        return jsonify({'success': True})
    return jsonify({'error': 'Failed to toggle auto-sync'}), 500


@app.route('/admin/api/keys/<api_key_hash>', methods=['DELETE'])
def admin_delete_key(api_key_hash):
    """Delete all data for a specific API key"""
    admin_pass = os.environ.get('ADMIN_PASS')
    auth_token = request.cookies.get('admin_auth')
    
    if not admin_pass or auth_token != admin_pass:
        return jsonify({'error': 'Unauthorized'}), 401
    
    from lib.admin_utils import delete_key_data
    
    success = delete_key_data(api_key_hash)
    
    if success:
        return jsonify({'success': True})
    return jsonify({'error': 'Failed to delete data'}), 500


# Error Handlers
@app.errorhandler(404)
def not_found(e):
    return render_template('error.html', error='Page not found'), 404


@app.errorhandler(500)
def server_error(e):
    logger.error(f"Server error: {e}")
    return render_template('error.html', error='Internal server error'), 500


if __name__ == '__main__':
    # Start auto-sync scheduler when running directly
    try:
        auto_sync_scheduler.start()
        logger.info("Auto-sync scheduler initialized")
    except Exception as e:
        logger.error(f"Failed to start auto-sync scheduler: {e}")
    
    # Only run in debug mode if not in production
    debug_mode = os.environ.get('FLASK_ENV', 'development') != 'production'
    app.run(debug=debug_mode, host='0.0.0.0', port=5000)
