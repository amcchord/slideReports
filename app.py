"""
Slide Reports System - Main Flask Application
"""
import os
import json
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
from lib.report_generator import ReportGenerator, format_datetime_friendly
from lib.background_sync import background_sync
from lib.scheduler import auto_sync_scheduler
from lib.email_schedules import EmailScheduleManager
from lib.email_service import EmailService
from lib.email_scheduler import EmailScheduler
from lib.pdf_service import PDFService
import pytz
import re

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

# Initialize email service
postmark_api_key = os.environ.get('POSTMARK_API_KEY')
if not postmark_api_key:
    logger.warning("POSTMARK_API_KEY not set - email functionality will be disabled")
    email_service = None
    email_scheduler = None
else:
    email_service = EmailService(postmark_api_key)
    email_scheduler = EmailScheduler(email_service)


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


def get_validated_timezone(db: Database) -> str:
    """
    Get validated timezone from database preferences.
    Falls back to America/New_York if timezone is invalid.
    
    Args:
        db: Database instance
    
    Returns:
        Valid timezone string
    """
    import pytz
    
    timezone = db.get_preference('timezone', 'America/New_York')
    
    # Validate timezone
    try:
        pytz.timezone(timezone)
        return timezone
    except pytz.exceptions.UnknownTimeZoneError:
        logger.warning(f'Invalid timezone "{timezone}" in database, falling back to America/New_York')
        # Update database with valid timezone
        db.set_preference('timezone', 'America/New_York')
        return 'America/New_York'


# Context Processors
@app.context_processor
def inject_custom_logo():
    """Make custom logo available to all templates"""
    api_key, api_key_hash = get_api_key_from_cookie()
    if api_key_hash:
        db = Database(get_database_path(api_key_hash))
        custom_logo = db.get_preference('custom_logo_base64')
        if custom_logo:
            return {'custom_logo_url': custom_logo}
    return {'custom_logo_url': None}


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
    """API key setup page with auto-login support"""
    # Define the special key that can always auto-login
    SPECIAL_KEY = 'tk_4xgc378i7hfe_Ww1yeInkVpxy0Y2JBlClo6IvJjCLpQzL'
    
    # Check for auto-login via URL parameter
    api_key_param = request.args.get('api_key')
    
    if api_key_param:
        # Check security: allow if no existing cookie OR if it's the special key
        existing_key, _ = get_api_key_from_cookie()
        
        if not existing_key or api_key_param == SPECIAL_KEY:
            # Validate API key format
            if Encryption.validate_api_key_format(api_key_param):
                # Test API key
                try:
                    client = SlideAPIClient(api_key_param)
                    if client.test_connection():
                        # Encrypt and set cookie
                        encrypted_key = encryption.encrypt(api_key_param)
                        api_key_hash = Encryption.hash_api_key(api_key_param)
                        
                        # Store in database
                        db = Database(get_database_path(api_key_hash))
                        db.store_encrypted_api_key(api_key_hash, encrypted_key)
                        
                        # Set cookie and redirect
                        response = redirect(url_for('dashboard'))
                        response.set_cookie(
                            'slide_api_key',
                            encrypted_key,
                            max_age=30*24*60*60,
                            httponly=True,
                            secure=request.is_secure,
                            samesite='Lax'
                        )
                        return response
                    else:
                        logger.warning(f"Auto-login failed: API key validation failed")
                except Exception as e:
                    logger.warning(f"Auto-login failed for API key: {e}")
            else:
                logger.warning(f"Auto-login failed: Invalid API key format")
        else:
            logger.info(f"Auto-login blocked: User already has a valid session")
    
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
    
    # Store encrypted API key in database for auto-sync
    api_key_hash = Encryption.hash_api_key(api_key)
    db = Database(get_database_path(api_key_hash))
    db.store_encrypted_api_key(api_key_hash, encrypted_key)
    
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
    
    # Get validated timezone
    timezone = get_validated_timezone(db)
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
    
    # Get upcoming scheduled emails
    upcoming_schedules = []
    if email_service:
        esm = EmailScheduleManager(db.db_path)
        all_schedules = esm.list_schedules()
        now_utc = datetime.utcnow().isoformat()
        upcoming_schedules = [
            s for s in all_schedules 
            if s.get('enabled') == 1 and s.get('next_run_at') and s.get('next_run_at') > now_utc
        ]
        # Sort by next_run_at
        upcoming_schedules.sort(key=lambda x: x.get('next_run_at', ''))
        # Limit to next 5
        upcoming_schedules = upcoming_schedules[:5]
    
    return render_template('dashboard.html',
                         sync_status=sync_status,
                         counts=counts,
                         timezone=timezone,
                         is_syncing=bg_state.get('status') == 'syncing',
                         upcoming_schedules=upcoming_schedules)


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


@app.route('/api/data/clear', methods=['POST'])
@require_api_key
def api_data_clear(api_key, api_key_hash):
    """Clear all synced data while preserving preferences and schedules"""
    try:
        db_path = get_database_path(api_key_hash)
        db = Database(db_path)
        db.clear_sync_data()
        
        # Also clear the background sync state to ensure it doesn't think a sync is in progress
        background_sync.clear_sync_state(api_key_hash)
        
        logger.info(f"Cleared sync data for {api_key_hash[:8]}")
        return jsonify({'success': True, 'message': 'All synced data cleared successfully'}), 200
    except Exception as e:
        logger.error(f"Error clearing sync data: {e}")
        return jsonify({'error': 'Failed to clear data'}), 500


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
    
    # Get current counts
    counts = db.get_data_source_counts()
    
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
        'current_source': bg_state.get('current_source'),
        'counts': counts
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
    
    # Get user timezone and format dates
    db = Database(get_database_path(api_key_hash))
    timezone_str = db.get_preference('timezone', 'America/New_York')
    user_tz = pytz.timezone(timezone_str)
    
    # Format dates for display
    for template in templates:
        if template.get('created_at'):
            try:
                created_dt = datetime.fromisoformat(template['created_at'])
                template['created_at_friendly'] = format_datetime_friendly(created_dt, user_tz)
            except Exception:
                template['created_at_friendly'] = template['created_at']
        else:
            template['created_at_friendly'] = 'Unknown'
        
        if template.get('updated_at'):
            try:
                updated_dt = datetime.fromisoformat(template['updated_at'])
                template['updated_at_friendly'] = format_datetime_friendly(updated_dt, user_tz)
            except Exception:
                template['updated_at_friendly'] = template['updated_at']
        else:
            template['updated_at_friendly'] = 'Unknown'
    
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


@app.route('/templates/<template_id>')
@require_api_key
def templates_view(api_key, api_key_hash, template_id):
    """View/edit template"""
    # Convert to int (Flask's <int:> doesn't support negative numbers)
    try:
        template_id = int(template_id)
    except ValueError:
        return "Invalid template ID", 400
    
    tm = TemplateManager(api_key_hash)
    template = tm.get_template(template_id)
    
    if not template:
        return "Template not found", 404
    
    # Ensure is_builtin flag is set (safety check)
    if 'is_builtin' not in template:
        template['is_builtin'] = template_id < 0
    
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


@app.route('/api/templates/<template_id>', methods=['PATCH'])
@require_api_key
def api_templates_update(api_key, api_key_hash, template_id):
    """Update template"""
    # Convert to int (Flask's <int:> doesn't support negative numbers)
    try:
        template_id = int(template_id)
    except ValueError:
        return jsonify({'error': 'Invalid template ID'}), 400
    
    # Prevent editing built-in templates
    if template_id < 0:
        return jsonify({'error': 'Cannot edit built-in templates'}), 400
    
    data = request.get_json()
    
    tm = TemplateManager(api_key_hash)
    tm.update_template(
        template_id,
        name=data.get('name'),
        description=data.get('description'),
        html_content=data.get('html_content')
    )
    
    return jsonify({'success': True})


@app.route('/api/templates/<template_id>', methods=['DELETE'])
@require_api_key
def api_templates_delete(api_key, api_key_hash, template_id):
    """Delete template"""
    # Convert to int (Flask's <int:> doesn't support negative numbers)
    try:
        template_id = int(template_id)
    except ValueError:
        return jsonify({'error': 'Invalid template ID'}), 400
    
    # Prevent deleting built-in templates
    if template_id < 0:
        return jsonify({'error': 'Cannot delete built-in templates'}), 400
    
    tm = TemplateManager(api_key_hash)
    tm.delete_template(template_id)
    
    return '', 204


@app.route('/api/templates/<template_id>/clone', methods=['POST'])
@require_api_key
def api_templates_clone(api_key, api_key_hash, template_id):
    """Clone a template (built-in or user template)"""
    # Convert to int (Flask's <int:> doesn't support negative numbers)
    try:
        template_id = int(template_id)
    except ValueError:
        return jsonify({'error': 'Invalid template ID'}), 400
    
    tm = TemplateManager(api_key_hash)
    source_template = tm.get_template(template_id)
    
    if not source_template:
        return jsonify({'error': 'Template not found'}), 404
    
    # Create new name for cloned template
    original_name = source_template['name']
    clone_name = f"{original_name} (Copy)"
    
    # Create the cloned template
    new_template_id = tm.create_template(
        name=clone_name,
        description=source_template.get('description', ''),
        html_content=source_template['html_content']
    )
    
    return jsonify({
        'success': True,
        'template_id': new_template_id,
        'name': clone_name
    })


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


@app.route('/api/templates/generate-stream', methods=['POST'])
@require_api_key
def api_templates_generate_stream(api_key, api_key_hash):
    """Generate template with AI using streaming"""
    data = request.get_json()
    description = data.get('description')
    data_sources = data.get('data_sources', [])
    
    if not description:
        return jsonify({'error': 'Description required'}), 400
    
    def generate():
        """Generator function for streaming response"""
        try:
            # Call Claude API with streaming enabled
            data_sources_str = ", ".join(data_sources) if data_sources else "all data sources"
            
            rules_text = "\n".join([f"- {key}: {value}" for key, value in ai_generator.template_schema['important_rules'].items()])
            
            system_prompt = f"""You are an expert at creating professional, print-ready HTML report templates using Jinja2.

CRITICAL SAFETY RULES - FOLLOW THESE EXACTLY:
{rules_text}

Generate a complete, self-contained HTML document with embedded CSS that:
1. Is optimized for printing to PDF
2. Has a clean, professional design
3. Uses modern CSS (flexbox, grid) for layouts
4. Includes proper page break handling for printing
5. Has clear section headings and data visualization
6. Uses SAFE Jinja2 template syntax

Return ONLY the complete HTML document, no explanations."""

            user_prompt = f"""Create an HTML report template based on this description:

{description}

The template will use these data sources: {data_sources_str}

Include SAFE Jinja2 syntax for dynamic content. Make it professional and print-ready."""

            accumulated_text = ""
            
            # Stream from Claude
            with ai_generator.client.messages.stream(
                model=ai_generator.MODEL,
                max_tokens=16000,
                system=system_prompt,
                messages=[{
                    "role": "user",
                    "content": user_prompt
                }]
            ) as stream:
                for text in stream.text_stream:
                    accumulated_text += text
                    # Send chunk to client
                    yield f"data: {json.dumps({'chunk': text, 'done': False})}\n\n"
            
            # Clean up if Claude added markdown code blocks
            html_content = accumulated_text.strip()
            if html_content.startswith('```html'):
                html_content = html_content[7:]
            if html_content.startswith('```'):
                html_content = html_content[3:]
            if html_content.endswith('```'):
                html_content = html_content[:-3]
            html_content = html_content.strip()
            
            # Send final complete HTML
            yield f"data: {json.dumps({'html': html_content, 'done': True})}\n\n"
            
        except Exception as e:
            logger.error(f"Streaming template generation failed: {e}")
            yield f"data: {json.dumps({'error': str(e), 'done': True})}\n\n"
    
    return app.response_class(generate(), mimetype='text/event-stream')


@app.route('/api/templates/improve', methods=['POST'])
@require_api_key
def api_templates_improve(api_key, api_key_hash):
    """Improve existing template with AI"""
    data = request.get_json()
    current_html = data.get('current_html')
    improvement_request = data.get('improvement_request')
    
    if not current_html:
        return jsonify({'error': 'Current HTML required'}), 400
    
    if not improvement_request:
        return jsonify({'error': 'Improvement request required'}), 400
    
    try:
        improved_html = ai_generator.improve_template(current_html, improvement_request)
        return jsonify({'improved_html': improved_html})
    except Exception as e:
        logger.error(f"Template improvement failed: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/templates/test', methods=['POST'])
@require_api_key
def api_templates_test(api_key, api_key_hash):
    """Test template with real user data"""
    data = request.get_json()
    html_content = data.get('html_content')
    start_date_str = data.get('start_date')
    end_date_str = data.get('end_date')
    data_sources = data.get('data_sources', [])
    client_id = data.get('client_id')
    
    if not html_content:
        return jsonify({'error': 'HTML content required'}), 400
    
    # Parse dates
    start_date = datetime.fromisoformat(start_date_str) if start_date_str else None
    end_date = datetime.fromisoformat(end_date_str) if end_date_str else None
    
    # Generate report with error handling
    db = Database(get_database_path(api_key_hash))
    generator = ReportGenerator(db)
    
    try:
        html = generator.generate_report(
            html_content,
            start_date,
            end_date,
            data_sources,
            logo_url='/static/img/logo.png',
            client_id=client_id,
            ai_generator=ai_generator
        )
        return jsonify({'success': True, 'html': html})
    except Exception as e:
        logger.error(f"Template test failed: {e}")
        # Return detailed error for debugging
        import traceback
        error_detail = traceback.format_exc()
        return jsonify({
            'success': False,
            'error': str(e),
            'error_detail': error_detail
        }), 400


@app.route('/api/templates/fix-error', methods=['POST'])
@require_api_key
def api_templates_fix_error(api_key, api_key_hash):
    """Fix template error with AI"""
    data = request.get_json()
    html_content = data.get('html_content')
    error_message = data.get('error_message')
    
    if not html_content:
        return jsonify({'error': 'HTML content required'}), 400
    
    if not error_message:
        return jsonify({'error': 'Error message required'}), 400
    
    try:
        fixed_html, explanation = ai_generator.fix_template_error(html_content, error_message)
        return jsonify({
            'fixed_html': fixed_html,
            'explanation': explanation
        })
    except Exception as e:
        logger.error(f"Template error fix failed: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/reports/builder')
@require_api_key
def reports_builder(api_key, api_key_hash):
    """Report builder interface"""
    tm = TemplateManager(api_key_hash)
    templates = tm.list_templates()
    
    db = Database(get_database_path(api_key_hash))
    counts = db.get_data_source_counts()
    timezone = get_validated_timezone(db)
    
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


@app.route('/api/reports/download', methods=['POST'])
@require_api_key
def api_reports_download(api_key, api_key_hash):
    """Generate and download report as standalone HTML with embedded images"""
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
    
    # Generate report with base64 images
    db = Database(get_database_path(api_key_hash))
    generator = ReportGenerator(db)
    
    try:
        html = generator.generate_report_with_base64_images(
            template['html_content'],
            start_date,
            end_date,
            data_sources,
            logo_url='/static/img/logo.png',
            client_id=client_id,
            ai_generator=ai_generator
        )
        
        # Create filename with date
        if start_date and end_date:
            filename = f"backup-report-{start_date.strftime('%Y-%m-%d')}-to-{end_date.strftime('%Y-%m-%d')}.html"
        else:
            filename = f"backup-report-{datetime.now().strftime('%Y-%m-%d')}.html"
        
        # Return as downloadable file
        response = make_response(html)
        response.headers['Content-Type'] = 'text/html; charset=utf-8'
        response.headers['Content-Disposition'] = f'attachment; filename="{filename}"'
        
        return response
    except Exception as e:
        logger.error(f"Report download generation failed: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/preferences/timezone', methods=['POST'])
@require_api_key
def api_set_timezone(api_key, api_key_hash):
    """Set user timezone preference"""
    data = request.get_json()
    timezone = data.get('timezone')
    
    if not timezone:
        return jsonify({'error': 'Timezone required'}), 400
    
    # Validate timezone using pytz
    try:
        pytz.timezone(timezone)
    except pytz.exceptions.UnknownTimeZoneError:
        # Fall back to Eastern Standard Time if timezone is invalid
        timezone = 'America/New_York'
        logger.warning(f'Invalid timezone provided, falling back to {timezone}')
    
    db = Database(get_database_path(api_key_hash))
    db.set_preference('timezone', timezone)
    
    return jsonify({'success': True, 'timezone': timezone})


@app.route('/api/preferences/logo', methods=['POST'])
@require_api_key
def api_upload_logo(api_key, api_key_hash):
    """Upload and save custom logo"""
    import base64
    import imghdr
    
    if 'logo' not in request.files:
        return jsonify({'error': 'No logo file provided'}), 400
    
    file = request.files['logo']
    
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    # Read file data
    file_data = file.read()
    
    # Validate file size (2MB max)
    if len(file_data) > 2 * 1024 * 1024:
        return jsonify({'error': 'File size exceeds 2MB limit'}), 400
    
    # Validate file type
    file_type = imghdr.what(None, h=file_data)
    allowed_types = ['png', 'jpeg', 'gif', 'svg']
    
    # Special handling for SVG (imghdr doesn't detect SVG)
    if file_type is None:
        if file_data.startswith(b'<svg') or b'<svg' in file_data[:1024]:
            file_type = 'svg'
    
    if file_type not in allowed_types:
        return jsonify({'error': 'Invalid file type. Allowed: PNG, JPG, GIF, SVG'}), 400
    
    # Determine MIME type
    mime_types = {
        'png': 'image/png',
        'jpeg': 'image/jpeg',
        'gif': 'image/gif',
        'svg': 'image/svg+xml'
    }
    mime_type = mime_types.get(file_type, 'image/png')
    
    # Convert to base64
    base64_data = base64.b64encode(file_data).decode('utf-8')
    data_uri = f'data:{mime_type};base64,{base64_data}'
    
    # Store in database
    db = Database(get_database_path(api_key_hash))
    db.set_preference('custom_logo_base64', data_uri)
    
    logger.info(f"Custom logo uploaded for user {api_key_hash[:8]}")
    
    return jsonify({'success': True, 'message': 'Logo uploaded successfully', 'logo_url': data_uri})


@app.route('/api/preferences/logo', methods=['DELETE'])
@require_api_key
def api_delete_logo(api_key, api_key_hash):
    """Reset to default logo"""
    db = Database(get_database_path(api_key_hash))
    
    # Delete the custom logo preference
    with db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM user_preferences WHERE key = ?", ('custom_logo_base64',))
    
    logger.info(f"Custom logo deleted for user {api_key_hash[:8]}")
    
    return jsonify({'success': True, 'message': 'Logo reset to default'})


@app.route('/logo-settings')
@require_api_key
def logo_settings(api_key, api_key_hash):
    """Logo management page"""
    db = Database(get_database_path(api_key_hash))
    custom_logo = db.get_preference('custom_logo_base64')
    
    return render_template('logo_settings.html', custom_logo=custom_logo)


@app.route('/report-values')
@require_api_key
def report_values_docs(api_key, api_key_hash):
    """Documentation page for all available report template variables"""
    return render_template('report_values.html')


@app.route('/email-reports')
@require_api_key
def email_reports_page(api_key, api_key_hash):
    """Email schedules management page"""
    if not email_service:
        return render_template('error.html', error='Email functionality is not configured. Please set POSTMARK_API_KEY in environment.'), 503
    
    return render_template('email_reports.html')


@app.route('/email-reports/create')
@require_api_key
def email_reports_create(api_key, api_key_hash):
    """Create email schedule page"""
    if not email_service:
        return render_template('error.html', error='Email functionality is not configured. Please set POSTMARK_API_KEY in environment.'), 503
    
    # Get templates for dropdown
    tm = TemplateManager(api_key_hash)
    templates = tm.list_templates()
    
    # Get clients for optional filtering
    db = Database(get_database_path(api_key_hash))
    clients = db.get_records('clients', order_by='name')
    timezone = get_validated_timezone(db)
    
    return render_template('email_reports_create.html', 
                         templates=templates,
                         clients=clients,
                         timezone=timezone)


@app.route('/email-reports/edit/<int:schedule_id>')
@require_api_key
def email_reports_edit(api_key, api_key_hash, schedule_id):
    """Edit email schedule page"""
    if not email_service:
        return render_template('error.html', error='Email functionality is not configured. Please set POSTMARK_API_KEY in environment.'), 503
    
    # Get the schedule
    db_path = get_database_path(api_key_hash)
    esm = EmailScheduleManager(db_path)
    schedule = esm.get_schedule(schedule_id)
    
    if not schedule:
        return render_template('error.html', error='Schedule not found'), 404
    
    # Get templates for dropdown
    tm = TemplateManager(api_key_hash)
    templates = tm.list_templates()
    
    # Get clients for optional filtering
    db = Database(db_path)
    clients = db.get_records('clients', order_by='name')
    timezone = get_validated_timezone(db)
    
    return render_template('email_reports_edit.html', 
                         templates=templates,
                         clients=clients,
                         timezone=timezone,
                         schedule=schedule)


@app.route('/email-reports/log')
@require_api_key
def email_reports_log(api_key, api_key_hash):
    """Email send log page"""
    if not email_service:
        return render_template('error.html', error='Email functionality is not configured. Please set POSTMARK_API_KEY in environment.'), 503
    
    db_path = get_database_path(api_key_hash)
    db = Database(db_path)
    
    # Get email send log with schedule names
    with db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT 
                l.log_id,
                l.schedule_id,
                l.sent_at,
                l.status,
                l.error_message,
                l.recipient_email,
                l.report_date_range,
                s.name as schedule_name
            FROM email_send_log l
            LEFT JOIN email_schedules s ON l.schedule_id = s.schedule_id
            ORDER BY l.sent_at DESC
            LIMIT 100
        """)
        logs = [dict(row) for row in cursor.fetchall()]
    
    return render_template('email_log.html', logs=logs)


@app.route('/api/email-schedules', methods=['GET'])
@require_api_key
def api_email_schedules_list(api_key, api_key_hash):
    """Get all email schedules"""
    if not email_service:
        return jsonify({'error': 'Email functionality not configured'}), 503
    
    db_path = get_database_path(api_key_hash)
    esm = EmailScheduleManager(db_path)
    schedules = esm.list_schedules()
    
    # Enrich with template names
    tm = TemplateManager(api_key_hash)
    for schedule in schedules:
        template = tm.get_template(schedule['template_id'])
        schedule['template_name'] = template['name'] if template else 'Unknown Template'
    
    # Enrich with client names if applicable
    db = Database(db_path)
    for schedule in schedules:
        if schedule.get('client_id'):
            clients = db.get_records('clients', where='client_id = ?', params=(schedule['client_id'],))
            schedule['client_name'] = clients[0]['name'] if clients else 'Unknown Client'
        else:
            schedule['client_name'] = 'All Clients'
    
    return jsonify(schedules)


@app.route('/api/email-schedules', methods=['POST'])
@require_api_key
def api_email_schedules_create(api_key, api_key_hash):
    """Create new email schedule"""
    if not email_service:
        return jsonify({'error': 'Email functionality not configured'}), 503
    
    data = request.get_json()
    name = data.get('name', '').strip()
    email_address = data.get('email_address', '').strip()
    template_id = data.get('template_id')
    date_range_type = data.get('date_range_type', '').strip()
    client_id = data.get('client_id')
    attachment_format = data.get('attachment_format', 'html').strip()
    email_subject = data.get('email_subject')
    email_body = data.get('email_body')
    
    # Validation
    if not name:
        return jsonify({'error': 'Name is required'}), 400
    
    if not email_address:
        return jsonify({'error': 'Email address is required'}), 400
    
    # Validate email format
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(email_pattern, email_address):
        return jsonify({'error': 'Invalid email address format'}), 400
    
    if template_id is None:
        return jsonify({'error': 'Template is required'}), 400
    
    # Validate template exists
    tm = TemplateManager(api_key_hash)
    template = tm.get_template(int(template_id))
    if not template:
        return jsonify({'error': 'Template not found'}), 404
    
    # Validate date range type
    valid_date_ranges = ['last_day', '7_days', '30_days', '90_days']
    if date_range_type not in valid_date_ranges:
        return jsonify({'error': 'Invalid date range type'}), 400
    
    # Validate attachment format
    valid_formats = ['html', 'pdf', 'both']
    if attachment_format not in valid_formats:
        return jsonify({'error': 'Invalid attachment format'}), 400
    
    # Get scheduling parameters
    schedule_frequency = data.get('schedule_frequency')
    schedule_time = data.get('schedule_time')
    schedule_day_of_week = data.get('schedule_day_of_week')
    schedule_day_of_month = data.get('schedule_day_of_month')
    
    # Validate scheduling parameters if frequency is set
    if schedule_frequency:
        valid_frequencies = ['daily', 'weekly', 'monthly']
        if schedule_frequency not in valid_frequencies:
            return jsonify({'error': 'Invalid schedule frequency'}), 400
        
        if not schedule_time:
            return jsonify({'error': 'Schedule time is required when frequency is set'}), 400
        
        # Validate time format
        if not re.match(r'^\d{2}:\d{2}$', schedule_time):
            return jsonify({'error': 'Invalid time format. Use HH:MM'}), 400
        
        if schedule_frequency == 'weekly' and schedule_day_of_week is None:
            return jsonify({'error': 'Day of week is required for weekly schedules'}), 400
        
        if schedule_frequency == 'monthly' and schedule_day_of_month is None:
            return jsonify({'error': 'Day of month is required for monthly schedules'}), 400
    
    # Get user's timezone
    db_path = get_database_path(api_key_hash)
    db = Database(db_path)
    timezone = get_validated_timezone(db)
    
    # Create schedule
    esm = EmailScheduleManager(db_path)
    schedule_id = esm.create_schedule(
        name=name,
        email_address=email_address,
        template_id=int(template_id),
        date_range_type=date_range_type,
        client_id=client_id if client_id else None,
        attachment_format=attachment_format,
        email_subject=email_subject,
        email_body=email_body,
        schedule_frequency=schedule_frequency,
        schedule_time=schedule_time,
        schedule_day_of_week=int(schedule_day_of_week) if schedule_day_of_week is not None else None,
        schedule_day_of_month=int(schedule_day_of_month) if schedule_day_of_month is not None else None,
        timezone=timezone
    )
    
    return jsonify({'success': True, 'schedule_id': schedule_id}), 201


@app.route('/api/email-schedules/<int:schedule_id>', methods=['GET'])
@require_api_key
def api_email_schedules_get(api_key, api_key_hash, schedule_id):
    """Get single email schedule"""
    if not email_service:
        return jsonify({'error': 'Email functionality not configured'}), 503
    
    db_path = get_database_path(api_key_hash)
    esm = EmailScheduleManager(db_path)
    schedule = esm.get_schedule(schedule_id)
    
    if not schedule:
        return jsonify({'error': 'Schedule not found'}), 404
    
    return jsonify(schedule)


@app.route('/api/email-schedules/<int:schedule_id>', methods=['PATCH'])
@require_api_key
def api_email_schedules_update(api_key, api_key_hash, schedule_id):
    """Update email schedule"""
    if not email_service:
        return jsonify({'error': 'Email functionality not configured'}), 503
    
    data = request.get_json()
    
    # Validate email if provided
    if 'email_address' in data:
        email_address = data['email_address'].strip()
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, email_address):
            return jsonify({'error': 'Invalid email address format'}), 400
        data['email_address'] = email_address
    
    # Validate template if provided
    if 'template_id' in data:
        tm = TemplateManager(api_key_hash)
        template = tm.get_template(int(data['template_id']))
        if not template:
            return jsonify({'error': 'Template not found'}), 404
    
    # Validate date range type if provided
    if 'date_range_type' in data:
        valid_date_ranges = ['last_day', '7_days', '30_days', '90_days']
        if data['date_range_type'] not in valid_date_ranges:
            return jsonify({'error': 'Invalid date range type'}), 400
    
    # Validate attachment format if provided
    if 'attachment_format' in data:
        valid_formats = ['html', 'pdf', 'both']
        if data['attachment_format'] not in valid_formats:
            return jsonify({'error': 'Invalid attachment format'}), 400
    
    # Validate scheduling parameters if frequency is provided
    if 'schedule_frequency' in data:
        schedule_frequency = data.get('schedule_frequency')
        if schedule_frequency:
            valid_frequencies = ['daily', 'weekly', 'monthly']
            if schedule_frequency not in valid_frequencies:
                return jsonify({'error': 'Invalid schedule frequency'}), 400
            
            # If updating frequency, need time too
            if 'schedule_time' not in data:
                # Check if existing schedule has time
                db_path = get_database_path(api_key_hash)
                esm = EmailScheduleManager(db_path)
                existing = esm.get_schedule(schedule_id)
                if not existing or not existing.get('schedule_time'):
                    return jsonify({'error': 'Schedule time is required when frequency is set'}), 400
    
    # Get timezone for recalculation
    db_path = get_database_path(api_key_hash)
    db = Database(db_path)
    timezone = get_validated_timezone(db)
    
    # Add timezone to data for recalculation
    data['timezone'] = timezone
    
    # Convert day values to integers if present
    if 'schedule_day_of_week' in data and data['schedule_day_of_week'] is not None:
        data['schedule_day_of_week'] = int(data['schedule_day_of_week'])
    
    if 'schedule_day_of_month' in data and data['schedule_day_of_month'] is not None:
        data['schedule_day_of_month'] = int(data['schedule_day_of_month'])
    
    esm = EmailScheduleManager(db_path)
    esm.update_schedule(schedule_id, **data)
    
    return jsonify({'success': True})


@app.route('/api/email-schedules/<int:schedule_id>', methods=['DELETE'])
@require_api_key
def api_email_schedules_delete(api_key, api_key_hash, schedule_id):
    """Delete email schedule"""
    if not email_service:
        return jsonify({'error': 'Email functionality not configured'}), 503
    
    db_path = get_database_path(api_key_hash)
    esm = EmailScheduleManager(db_path)
    esm.delete_schedule(schedule_id)
    
    return '', 204


@app.route('/api/email-schedules/<int:schedule_id>/test', methods=['POST'])
@require_api_key
def api_email_schedules_test(api_key, api_key_hash, schedule_id):
    """Test send email for a schedule"""
    if not email_service:
        return jsonify({'error': 'Email functionality not configured'}), 503
    
    # Get schedule
    db_path = get_database_path(api_key_hash)
    esm = EmailScheduleManager(db_path)
    schedule = esm.get_schedule(schedule_id)
    
    if not schedule:
        return jsonify({'error': 'Schedule not found'}), 404
    
    # Calculate date range based on date_range_type
    db = Database(db_path)
    timezone_str = db.get_preference('timezone', 'America/New_York')
    user_tz = pytz.timezone(timezone_str)
    
    # Get "yesterday" in user's timezone
    now = datetime.now(user_tz)
    yesterday = now - timedelta(days=1)
    end_date = yesterday.replace(hour=23, minute=59, second=59, microsecond=999999)
    
    # Calculate start date based on range type
    date_range_type = schedule['date_range_type']
    if date_range_type == 'last_day':
        start_date = yesterday.replace(hour=0, minute=0, second=0, microsecond=0)
    elif date_range_type == '7_days':
        start_date = (yesterday - timedelta(days=6)).replace(hour=0, minute=0, second=0, microsecond=0)
    elif date_range_type == '30_days':
        start_date = (yesterday - timedelta(days=29)).replace(hour=0, minute=0, second=0, microsecond=0)
    elif date_range_type == '90_days':
        start_date = (yesterday - timedelta(days=89)).replace(hour=0, minute=0, second=0, microsecond=0)
    else:
        return jsonify({'error': 'Invalid date range type'}), 400
    
    # Get template
    tm = TemplateManager(api_key_hash)
    template = tm.get_template(schedule['template_id'])
    
    if not template:
        return jsonify({'error': 'Template not found'}), 404
    
    # Determine data sources from template (we'll use all for now)
    # In a real implementation, you might parse the template to detect which data sources are needed
    data_sources = ['devices', 'agents', 'backups', 'snapshots', 'alerts', 'audits', 
                   'clients', 'users', 'networks', 'virtual_machines', 'file_restores', 
                   'image_exports', 'accounts']
    
    # Generate report HTML and get context for email rendering
    try:
        generator = ReportGenerator(db)
        html_content = generator.generate_report_with_base64_images(
            template['html_content'],
            start_date,
            end_date,
            data_sources,
            logo_url='/static/img/logo.png',
            client_id=schedule.get('client_id'),
            ai_generator=ai_generator
        )
        
        # Build context for email subject and body rendering
        email_context = generator._build_context(
            start_date, end_date, user_tz, data_sources, 
            '/static/img/logo.png', schedule.get('client_id')
        )
        
        # Add exec_summary to context if AI generator is available
        if ai_generator:
            try:
                email_context['exec_summary'] = ai_generator.generate_executive_summary(email_context)
            except Exception as e:
                logger.warning(f"AI summary generation failed: {e}")
                email_context['exec_summary'] = generator._generate_summary(email_context)
        else:
            email_context['exec_summary'] = email_context.get('executive_summary', generator._generate_summary(email_context))
        
    except Exception as e:
        logger.error(f"Report generation failed: {e}")
        return jsonify({'error': f'Report generation failed: {str(e)}'}), 500
    
    # Render email subject and body with template variables
    try:
        from jinja2 import Template as JinjaTemplate
        
        email_subject_template = JinjaTemplate(schedule['email_subject'] or "Slide Backup Report - {{ date_range }}")
        rendered_subject = email_subject_template.render(**email_context)
        
        email_body_template = JinjaTemplate(schedule['email_body'] or """Your Slide Backup Report for {{ date_range }} is ready.

Executive Summary:
{{ exec_summary }}

Key Metrics:
- Total Backups: {{ total_backups }}
- Success Rate: {{ success_rate }}%

Report generated at {{ generated_at }} ({{ timezone }})""")
        rendered_body = email_body_template.render(**email_context)
        
    except Exception as e:
        logger.error(f"Email template rendering failed: {e}")
        return jsonify({'error': f'Email template rendering failed: {str(e)}'}), 500
    
    # Generate attachments based on format preference
    attachment_format = schedule.get('attachment_format', 'html')
    date_str = end_date.strftime('%Y-%m-%d')
    
    pdf_content = None
    pdf_filename = None
    html_attachment_content = None
    html_attachment_filename = None
    
    if attachment_format in ['pdf', 'both']:
        try:
            pdf_content = PDFService.html_to_pdf(html_content)
            pdf_filename = f"slide-backup-report-{date_str}.pdf"
        except Exception as e:
            logger.error(f"PDF generation failed: {e}")
            return jsonify({'error': f'PDF generation failed: {str(e)}'}), 500
    
    if attachment_format in ['html', 'both']:
        html_attachment_content = html_content.encode('utf-8')
        html_attachment_filename = f"slide-backup-report-{date_str}.html"
    
    # Send email
    try:
        success, message = email_service.send_report_email(
            to_email=schedule['email_address'],
            subject=rendered_subject,
            text_body=rendered_body,
            pdf_content=pdf_content,
            pdf_filename=pdf_filename,
            html_content=html_attachment_content,
            html_filename=html_attachment_filename
        )
        
        if success:
            return jsonify({'success': True, 'message': 'Test email sent successfully'})
        else:
            return jsonify({'error': message}), 500
            
    except Exception as e:
        logger.error(f"Email send failed: {e}")
        return jsonify({'error': f'Failed to send email: {str(e)}'}), 500


@app.route('/api/template-schema.json')
@require_api_key
def api_template_schema(api_key, api_key_hash):
    """Get JSON schema of all template variables for LLM consumption"""
    schema = {
        "system": "Jinja2",
        "description": "Template variables for Slide backup reports. Use Jinja2 syntax: {{ variable }} for output, {% if condition %} for conditionals, {% for item in list %} for loops.",
        "documentation_url": "https://jinja.palletsprojects.com/",
        "variables": {
            "logo_url": {
                "type": "string",
                "description": "URL or path to logo image",
                "example": "/static/img/logo.png"
            },
            "report_title": {
                "type": "string",
                "description": "Title of the report",
                "example": "Slide Backup Report"
            },
            "date_range": {
                "type": "string",
                "description": "Human-readable date range for the report period",
                "example": "2025-01-01 - 2025-01-31"
            },
            "generated_at": {
                "type": "string",
                "description": "Timestamp when report was generated (in user timezone)",
                "example": "2025-10-15 14:30:00 EST"
            },
            "timezone": {
                "type": "string",
                "description": "User's timezone",
                "example": "America/New_York"
            },
            "client_id": {
                "type": "string|null",
                "description": "Client ID if filtering by client, null for all clients",
                "example": "client_123"
            },
            "client_name": {
                "type": "string",
                "description": "Client name (only present when filtering by client)",
                "example": "BiffCo"
            },
            "exec_summary": {
                "type": "string",
                "description": "AI-generated executive summary (auto-generated if placeholder is present)",
                "example": "During this reporting period, 148 backups were executed..."
            },
            "total_backups": {
                "type": "integer",
                "description": "Total number of backups in reporting period",
                "example": 148
            },
            "successful_backups": {
                "type": "integer",
                "description": "Number of successful backups",
                "example": 141
            },
            "failed_backups": {
                "type": "integer",
                "description": "Number of failed backups",
                "example": 7
            },
            "success_rate": {
                "type": "float",
                "description": "Success percentage (0-100)",
                "example": 95.3
            },
            "agent_backup_status": {
                "type": "array",
                "description": "List of per-agent backup status",
                "item_type": "object",
                "properties": {
                    "name": "Agent display name",
                    "last_backup": "Formatted datetime",
                    "status": "Status string (Succeeded/Failed/Running)",
                    "status_class": "CSS class (success/danger/warning)",
                    "duration": "Formatted duration string"
                }
            },
            "active_snapshots": {
                "type": "integer",
                "description": "Number of active (not deleted) snapshots",
                "example": 126
            },
            "deleted_snapshots": {
                "type": "integer",
                "description": "Number of deleted snapshots",
                "example": 34
            },
            "local_snapshots": {
                "type": "integer",
                "description": "Number of snapshots in local storage",
                "example": 50
            },
            "cloud_snapshots": {
                "type": "integer",
                "description": "Number of snapshots in cloud storage",
                "example": 76
            },
            "latest_screenshot": {
                "type": "object|null",
                "description": "Latest verification screenshot",
                "properties": {
                    "url": "Image URL",
                    "agent_name": "Agent name",
                    "captured_at": "Formatted datetime"
                }
            },
            "total_alerts": {
                "type": "integer",
                "description": "Total alerts in reporting period",
                "example": 12
            },
            "unresolved_alerts": {
                "type": "integer",
                "description": "Number of unresolved alerts",
                "example": 3
            },
            "resolved_alerts": {
                "type": "integer",
                "description": "Number of resolved alerts",
                "example": 9
            },
            "device_storage": {
                "type": "array",
                "description": "List of devices with storage info",
                "item_type": "object",
                "properties": {
                    "name": "Device name",
                    "used": "Used storage (formatted)",
                    "total": "Total storage (formatted)",
                    "percent": "Usage percentage (0-100)"
                }
            },
            "agent_snapshot_totals": {
                "type": "array",
                "description": "List of snapshot totals per agent showing local and cloud snapshot counts",
                "item_type": "object",
                "properties": {
                    "agent_name": "Agent display name",
                    "local_count": "Number of snapshots in local storage",
                    "cloud_count": "Number of snapshots in cloud storage"
                }
            },
            "agent_snapshot_audit": {
                "type": "array",
                "description": "Complete snapshot audit data grouped by agent with verification status and location details",
                "item_type": "object",
                "properties": {
                    "agent_name": "Agent display name",
                    "agent_id": "Agent ID",
                    "snapshots": "Array of snapshot objects with: date_formatted (string), location_local (boolean), location_cloud (boolean), verify_boot_passed (boolean), verify_fs_passed (boolean), screenshot_url (string|None)"
                }
            },
            "total_vms": {
                "type": "integer",
                "description": "Total number of virtual machines",
                "example": 5
            },
            "running_vms": {
                "type": "integer",
                "description": "Number of running VMs",
                "example": 4
            },
            "stopped_vms": {
                "type": "integer",
                "description": "Number of stopped VMs",
                "example": 1
            },
            "agent_calendars": {
                "type": "array",
                "description": "Calendar grid data per agent showing daily backup/snapshot status",
                "item_type": "object",
                "properties": {
                    "agent_name": "Agent name",
                    "agent_id": "Agent ID",
                    "calendar_grid": "Array of day objects (see below)"
                }
            },
            "agent_screenshots": {
                "type": "array",
                "description": "Screenshot pairs (oldest and newest) per agent",
                "item_type": "object",
                "properties": {
                    "agent_name": "Agent name",
                    "agent_id": "Agent ID",
                    "oldest_screenshot": "Screenshot object (url, date, snapshot_id)",
                    "newest_screenshot": "Screenshot object (url, date, snapshot_id)"
                }
            },
            "storage_growth": {
                "type": "object",
                "description": "Overall storage growth metrics",
                "properties": {
                    "start_bytes": "Storage at period start (bytes)",
                    "end_bytes": "Storage at period end (bytes)",
                    "growth_bytes": "Net change (bytes)",
                    "growth_percent": "Percentage change",
                    "start_formatted": "Formatted start storage",
                    "end_formatted": "Formatted end storage",
                    "growth_formatted": "Formatted growth",
                    "is_growth": "Boolean (true if growing, false if shrinking)"
                }
            },
            "device_storage_growth": {
                "type": "array",
                "description": "Per-device storage growth breakdown",
                "item_type": "object",
                "properties": {
                    "device_name": "Device name",
                    "start_bytes": "Start storage (bytes)",
                    "end_bytes": "End storage (bytes)",
                    "growth_bytes": "Net change",
                    "growth_percent": "Percentage change",
                    "start_formatted": "Formatted values",
                    "end_formatted": "Formatted values",
                    "growth_formatted": "Formatted values",
                    "is_growth": "Boolean"
                }
            },
            "devices": {
                "type": "array",
                "description": "Raw list of devices (database records) - filtered by client_id if specified",
                "warning": "Fields may be None/null. Always check before using! Datetime fields are ISO strings.",
                "item_type": "object",
                "properties": {
                    "device_id": "string - Unique device identifier",
                    "display_name": "string|None - Human-readable device name",
                    "hostname": "string|None - Device hostname",
                    "last_seen_at": "string (ISO format)|None - Last contact time (STRING, not datetime!)",
                    "booted_at": "string (ISO format)|None - Boot time (STRING)",
                    "ip_addresses": "string|None - JSON string of IP addresses",
                    "os": "string|None - Operating system",
                    "os_version": "string|None - OS version",
                    "arch": "string|None - Architecture (x86_64, arm64, etc.)",
                    "client_id": "string|None - Associated client ID",
                    "storage_used_bytes": "integer|None - Used storage in bytes",
                    "storage_total_bytes": "integer|None - Total storage in bytes"
                }
            },
            "agents": {
                "type": "array",
                "description": "Raw list of agents (database records) - filtered by client_id if specified",
                "warning": "Fields may be None/null. Always check before using! Datetime fields are ISO strings.",
                "item_type": "object",
                "properties": {
                    "agent_id": "string - Unique agent identifier",
                    "device_id": "string|None - Associated device ID",
                    "display_name": "string|None - Human-readable agent name",
                    "hostname": "string|None - Agent hostname",
                    "last_seen_at": "string (ISO format)|None - Last contact time (STRING)",
                    "booted_at": "string (ISO format)|None - Boot time (STRING)",
                    "ip_addresses": "string|None - JSON string of IP addresses",
                    "os": "string|None - Operating system",
                    "os_version": "string|None - OS version",
                    "arch": "string|None - Architecture",
                    "client_id": "string|None - Associated client ID"
                }
            },
            "backups": {
                "type": "array",
                "description": "Raw list of backups in the reporting period - filtered by client_id if specified",
                "warning": "Fields may be None/null. Always check before using! Datetime fields are ISO strings.",
                "item_type": "object",
                "properties": {
                    "backup_id": "string - Unique backup identifier",
                    "agent_id": "string - Associated agent ID",
                    "started_at": "string (ISO format)|None - Backup start time (STRING, not datetime!)",
                    "ended_at": "string (ISO format)|None - Backup end time (STRING)",
                    "status": "string - Status: 'succeeded', 'failed', 'running'",
                    "error_code": "integer|None - Error code if failed",
                    "error_message": "string|None - Error message if failed",
                    "snapshot_id": "string|None - Associated snapshot ID"
                }
            },
            "snapshots": {
                "type": "array",
                "description": "Raw list of snapshots in the reporting period - filtered by client_id if specified",
                "warning": "Fields may be None/null. Always check before using! Datetime fields are ISO strings.",
                "item_type": "object",
                "properties": {
                    "snapshot_id": "string - Unique snapshot identifier",
                    "agent_id": "string - Associated agent ID",
                    "backup_started_at": "string (ISO format)|None - Backup start time (STRING)",
                    "backup_ended_at": "string (ISO format)|None - Backup end time (STRING)",
                    "locations": "string|None - JSON string of storage locations",
                    "deleted": "string|None - Deletion status",
                    "deletions": "string|None - JSON string of deletion records",
                    "verify_boot_screenshot_url": "string|None - URL to boot verification screenshot",
                    "exists_local": "boolean - Exists in local storage",
                    "exists_cloud": "boolean - Exists in cloud storage",
                    "exists_deleted": "boolean - Has been deleted",
                    "exists_deleted_retention": "boolean - Deleted by retention policy",
                    "exists_deleted_manual": "boolean - Manually deleted"
                }
            },
            "alerts": {
                "type": "array",
                "description": "Raw list of alerts in the reporting period - filtered by client_id if specified",
                "warning": "Fields may be None/null. Always check before using! Datetime fields are ISO strings.",
                "item_type": "object",
                "properties": {
                    "alert_id": "string - Unique alert identifier",
                    "alert_type": "string - Alert type/category",
                    "alert_fields": "string|None - JSON string of alert fields",
                    "created_at": "string (ISO format)|None - Alert creation time (STRING)",
                    "resolved": "integer - 0 for unresolved, 1 for resolved (use as boolean)",
                    "device_id": "string|None - Associated device ID",
                    "agent_id": "string|None - Associated agent ID"
                }
            },
            "virtual_machines": {
                "type": "array",
                "description": "Raw list of VMs (database records) - filtered by client_id if specified",
                "warning": "Fields may be None/null. Always check before using! Datetime fields are ISO strings.",
                "item_type": "object",
                "properties": {
                    "virt_id": "string - Unique VM identifier",
                    "device_id": "string|None - Associated device ID",
                    "agent_id": "string|None - Associated agent ID",
                    "snapshot_id": "string|None - Associated snapshot ID",
                    "state": "string - VM state: 'running', 'stopped', etc.",
                    "created_at": "string (ISO format)|None - VM creation time (STRING)",
                    "expires_at": "string (ISO format)|None - VM expiration time (STRING)",
                    "cpu_count": "integer|None - Number of CPUs",
                    "memory_in_mb": "integer|None - Memory in megabytes"
                }
            },
            "file_restores": {
                "type": "array",
                "description": "Raw list of file restores (database records) - filtered by client_id if specified",
                "warning": "Fields may be None/null. Always check before using! Datetime fields are ISO strings.",
                "item_type": "object",
                "properties": {
                    "file_restore_id": "string - Unique file restore identifier",
                    "device_id": "string|None - Associated device ID",
                    "agent_id": "string|None - Associated agent ID",
                    "snapshot_id": "string|None - Associated snapshot ID",
                    "created_at": "string (ISO format)|None - Restore creation time (STRING)",
                    "expires_at": "string (ISO format)|None - Restore expiration time (STRING)"
                }
            },
            "clients": {
                "type": "array",
                "description": "Raw list of clients (database records) - only the filtered client if client_id specified",
                "warning": "Fields may be None/null. Always check before using!",
                "item_type": "object",
                "properties": {
                    "client_id": "string - Unique client identifier",
                    "name": "string|None - Client name",
                    "comments": "string|None - Client comments/notes"
                }
            },
            "audits": {
                "type": "array",
                "description": "Raw list of audit log entries in the reporting period (max 100) - filtered by client_id if specified",
                "warning": "Fields may be None/null. Always check before using! Datetime fields are ISO strings.",
                "item_type": "object",
                "properties": {
                    "audit_id": "string - Unique audit entry identifier",
                    "audit_time": "string (ISO format) - Audit timestamp (STRING)",
                    "account_id": "string|None - Associated account ID",
                    "client_id": "string|None - Associated client ID",
                    "user_id": "string|None - Associated user ID",
                    "action": "string - Action performed (create, delete, update, etc.)",
                    "resource_type": "string|None - Type of resource affected",
                    "resource_id": "string|None - ID of resource affected",
                    "note": "string|None - Additional notes"
                }
            },
            "agent_config_overview": {
                "type": "object",
                "description": "Comprehensive configuration overview with devices grouped with their agents, including outlier detection",
                "properties": {
                    "devices": "array - List of device objects, each containing device_info and agents array",
                    "summary": "object - Summary statistics (total_devices, total_agents, slow_backup_count, old_backup_count, config_outlier_count)"
                },
                "device_structure": {
                    "device_info": "object - Full device configuration (all device fields from database)",
                    "agents": "array - List of agent objects with full config and backup info"
                },
                "agent_structure": {
                    "agent_info": "object - Full agent configuration (all agent fields including encryption_algorithm, platform, vss_writer_configs, passphrases, etc.)",
                    "last_successful_backup_date": "string - Formatted date of last successful backup (e.g. '9:24AM Oct 17th 2025 EDT')",
                    "last_backup_duration_minutes": "integer|None - Duration of last backup in minutes",
                    "last_backup_duration_seconds": "integer|None - Duration of last backup in seconds",
                    "is_slow_backup": "boolean - True if last backup took >30 minutes",
                    "is_old_backup": "boolean - True if last backup was >7 days ago",
                    "config_outlier": "boolean - True if agent config differs from majority",
                    "ip_addresses_formatted": "string - Formatted IP addresses as comma-separated string",
                    "last_seen_formatted": "string - Formatted last seen date (e.g. '9:24AM Oct 17th 2025 EDT')",
                    "last_screenshot_url": "string|None - URL to latest snapshot screenshot"
                },
                "example_usage": "{% for device_group in agent_config_overview.devices %}...{{ device_group.device_info.hostname }}...{% for agent in device_group.agents %}...{{ agent.agent_info.os }}...{% endfor %}{% endfor %}"
            }
        },
        "important_rules": {
            "datetime_handling": "All datetime fields are ISO format STRINGS, not datetime objects. You CANNOT use .days, .seconds, .strftime() directly! Use string formatting or check if None first.",
            "null_safety": "ALWAYS check if a value exists before using it. Use 'if variable' or 'variable or default' patterns.",
            "safe_filters": "Use safe filters: |length (not len()), |default('N/A'), variable or 'N/A'",
            "avoid_python_operations": "Do NOT use Python datetime operations like (datetime1 - datetime2).days - this will fail!",
            "avoid_complex_lookups": "Avoid selectattr with 'equalto' - it may fail. Use simple loops instead.",
            "safe_example": "{% if device.storage_used_bytes %}{{ (device.storage_used_bytes / 1024**3)|round(1) }} GB{% else %}N/A{% endif %}"
        },
        "jinja2_filters": {
            "description": "Available Jinja2 filters for template expressions",
            "filters": {
                "length": "Get length of list/string: {{ items|length }} or {{ name|length }}",
                "default": "Provide default value if None/missing: {{ var|default('N/A') }}",
                "round": "Round numbers: {{ 3.14159|round(2) }} outputs 3.14",
                "upper": "Uppercase string: {{ name|upper }}",
                "lower": "Lowercase string: {{ name|lower }}",
                "title": "Title case: {{ name|title }}",
                "capitalize": "Capitalize first letter: {{ word|capitalize }}",
                "join": "Join list with separator: {{ items|join(', ') }}",
                "replace": "Replace substring: {{ text|replace('old', 'new') }}",
                "trim": "Remove whitespace: {{ text|trim }}",
                "truncate": "Truncate to length: {{ text|truncate(50) }}",
                "abs": "Absolute value: {{ number|abs }}",
                "int": "Convert to integer: {{ value|int }}",
                "float": "Convert to float: {{ value|float }}",
                "string": "Convert to string: {{ value|string }}"
            },
            "slicing": "Use Python slicing syntax: items[:10] for first 10, items[5:] for all after 5, items[::2] for every other"
        },
        "safe_operations": {
            "description": "Safe operations available in Jinja2 templates",
            "math": "Use +, -, *, /, //, %, ** in expressions: {{ (value / 1024)|round(2) }}",
            "comparisons": "Use ==, !=, <, >, <=, >= in conditionals: {% if count > 10 %}",
            "logic": "Use 'and', 'or', 'not' in conditionals: {% if a and b %}",
            "membership": "'in' operator for lists/strings: {% if 'text' in string %} or {% if item in list %}",
            "string_concat": "Use ~ operator to concatenate: {{ first_name ~ ' ' ~ last_name }}",
            "ternary": "Inline if/else: {{ 'yes' if condition else 'no' }}",
            "none_coalescing": "Use 'or' for default values: {{ variable or 'default' }}"
        },
        "flags": {
            "show_backup_stats": "True if backups data source selected",
            "show_snapshots": "True if snapshots data source selected",
            "show_alerts": "True if alerts data source selected",
            "show_storage": "True if devices/storage data source selected",
            "show_audits": "True if audits data source selected",
            "show_virtualization": "True if virtual_machines data source selected"
        },
        "examples": [
            {
                "description": "Getting device or agent name (with fallbacks)",
                "code": "{{ device.display_name or device.hostname or device.device_id }}\n{{ agent.display_name or agent.hostname or agent.agent_id }}"
            },
            {
                "description": "Loop through all devices with safe name access",
                "code": "{% for device in devices %}\n  <h4>{{ device.display_name or device.hostname }}</h4>\n  <p>OS: {{ device.os or 'Unknown' }}</p>\n{% endfor %}"
            },
            {
                "description": "Loop through all agents",
                "code": "{% for agent in agents %}\n  <div>{{ agent.display_name or agent.hostname }}: {{ agent.os }}</div>\n{% endfor %}"
            },
            {
                "description": "Find backups for a specific agent",
                "code": "{% for agent in agents %}\n  <h3>{{ agent.display_name or agent.hostname }}</h3>\n  {% for backup in backups %}\n    {% if backup.agent_id == agent.agent_id %}\n      <p>{{ backup.started_at }}: {{ backup.status }}</p>\n    {% endif %}\n  {% endfor %}\n{% endfor %}"
            },
            {
                "description": "Display backup statistics with preprocessed data",
                "code": "{% if show_backup_stats %}\n  <h2>Backup Statistics</h2>\n  <p>Total: {{ total_backups }}, Success Rate: {{ success_rate }}%</p>\n{% endif %}"
            },
            {
                "description": "Loop through agent backup status (preprocessed)",
                "code": "{% for agent in agent_backup_status %}\n  <div>{{ agent.name }}: {{ agent.status }} ({{ agent.duration }})</div>\n{% endfor %}"
            },
            {
                "description": "Display device storage with null safety",
                "code": "{% for device in devices %}\n  <h4>{{ device.display_name or device.hostname }}</h4>\n  {% if device.storage_used_bytes and device.storage_total_bytes %}\n    <p>{{ (device.storage_used_bytes / 1024**3)|round(1) }} GB / {{ (device.storage_total_bytes / 1024**3)|round(1) }} GB</p>\n  {% else %}\n    <p>Storage: N/A</p>\n  {% endif %}\n{% endfor %}"
            },
            {
                "description": "Count items with length filter",
                "code": "<p>Devices: {{ devices|length }}</p>\n<p>Agents: {{ agents|length }}</p>\n<p>Backups: {{ backups|length }}</p>"
            }
        ]
    }
    
    return jsonify(schema)


@app.route('/logout')
def logout():
    """Clear API key cookie"""
    response = redirect(url_for('setup'))
    response.set_cookie('slide_api_key', '', max_age=0)
    return response


@app.route('/api/preferences/auto-sync', methods=['POST'])
@require_api_key
def api_set_auto_sync(api_key, api_key_hash):
    """Toggle auto-sync preference and/or update frequency"""
    data = request.get_json()
    enabled = data.get('enabled')
    frequency_hours = data.get('frequency_hours')
    
    db = Database(get_database_path(api_key_hash))
    
    if enabled is not None:
        db.set_preference('auto_sync_enabled', 'true' if enabled else 'false')
    
    if frequency_hours is not None:
        db.set_preference('auto_sync_frequency_hours', str(frequency_hours))
    
    return jsonify({
        'success': True,
        'enabled': enabled if enabled is not None else db.get_preference('auto_sync_enabled', 'true').lower() == 'true',
        'frequency_hours': frequency_hours if frequency_hours is not None else int(db.get_preference('auto_sync_frequency_hours', '1'))
    })


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
    
    from lib.admin_utils import list_all_api_keys, get_system_stats, format_bytes, list_all_email_schedules
    
    api_keys = list_all_api_keys()
    stats = get_system_stats()
    email_schedules = list_all_email_schedules() if email_service else []
    
    return render_template('admin.html', 
                         api_keys=api_keys, 
                         stats=stats,
                         email_schedules=email_schedules,
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


@app.route('/admin/api/email-schedules/<api_key_hash>/<int:schedule_id>', methods=['DELETE'])
def admin_delete_email_schedule(api_key_hash, schedule_id):
    """Delete an email schedule as admin"""
    admin_pass = os.environ.get('ADMIN_PASS')
    auth_token = request.cookies.get('admin_auth')
    
    if not admin_pass or auth_token != admin_pass:
        return jsonify({'error': 'Unauthorized'}), 401
    
    from lib.admin_utils import delete_email_schedule
    
    success = delete_email_schedule(api_key_hash, schedule_id)
    
    if success:
        return jsonify({'success': True})
    return jsonify({'error': 'Failed to delete schedule'}), 500


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
    
    # Start email scheduler if email service is configured
    if email_scheduler:
        try:
            email_scheduler.start()
            logger.info("Email scheduler initialized")
        except Exception as e:
            logger.error(f"Failed to start email scheduler: {e}")
    
    # Only run in debug mode if not in production
    debug_mode = os.environ.get('FLASK_ENV', 'development') != 'production'
    app.run(debug=debug_mode, host='0.0.0.0', port=5000)
