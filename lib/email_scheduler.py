"""
Background scheduler for automatic email report sending.
"""
import os
import logging
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from .database import Database, get_database_path
from .email_schedules import EmailScheduleManager
from .templates import TemplateManager
from .report_generator import ReportGenerator
from .email_service import EmailService
from .pdf_service import PDFService
import glob
import pytz
from datetime import timedelta

logger = logging.getLogger(__name__)


class EmailScheduler:
    """Manages automatic email sending for all API keys"""
    
    def __init__(self, email_service: EmailService):
        self.scheduler = BackgroundScheduler()
        self.email_service = email_service
        self.pdf_service = PDFService()
        self.data_dir = os.environ.get('DATA_DIR', '/var/www/reports.slide.recipes/data')
        self.started = False
    
    def start(self):
        """Start the scheduler"""
        if self.started:
            return
        
        # Schedule email check every 5 minutes
        self.scheduler.add_job(
            func=self._check_and_send_all,
            trigger=IntervalTrigger(minutes=5),
            id='email_send_check',
            name='Check and send scheduled emails',
            replace_existing=True
        )
        
        self.scheduler.start()
        self.started = True
        logger.info("Email scheduler started")
    
    def stop(self):
        """Stop the scheduler"""
        if self.scheduler.running:
            self.scheduler.shutdown()
            self.started = False
            logger.info("Email scheduler stopped")
    
    def _check_and_send_all(self):
        """Check all API keys and send due emails"""
        try:
            # Get all database files
            if not os.path.exists(self.data_dir):
                return
            
            db_files = [f for f in os.listdir(self.data_dir) 
                       if f.endswith('.db') and not f.endswith('_templates.db')]
            
            for db_file in db_files:
                api_key_hash = db_file.replace('.db', '')
                self._check_and_send_for_key(api_key_hash)
        
        except Exception as e:
            logger.error(f"Error in email scheduler check: {e}", exc_info=True)
    
    def _check_and_send_for_key(self, api_key_hash: str):
        """Check if a specific API key has due emails"""
        try:
            db_path = get_database_path(api_key_hash)
            if not os.path.exists(db_path):
                return
            
            db = Database(db_path)
            esm = EmailScheduleManager(db_path)
            
            # Get timezone for this user
            timezone = db.get_preference('timezone', 'America/New_York')
            
            # Get schedules due for execution
            due_schedules = esm.get_schedules_due()
            
            for schedule in due_schedules:
                logger.info(f"Executing schedule {schedule['schedule_id']} for {api_key_hash[:8]}")
                self._execute_schedule(api_key_hash, schedule, timezone)
        
        except Exception as e:
            logger.error(f"Error checking schedules for {api_key_hash[:8]}: {e}", exc_info=True)
    
    def _execute_schedule(self, api_key_hash: str, schedule: dict, timezone: str):
        """Execute a single email schedule"""
        db_path = get_database_path(api_key_hash)
        db = Database(db_path)
        esm = EmailScheduleManager(db_path)
        
        try:
            # Calculate date range
            user_tz = pytz.timezone(timezone)
            now = datetime.now(user_tz)
            yesterday = now - timedelta(days=1)
            end_date = yesterday.replace(hour=23, minute=59, second=59, microsecond=999999)
            
            date_range_type = schedule['date_range_type']
            if date_range_type == 'last_day':
                start_date = yesterday.replace(hour=0, minute=0, second=0, microsecond=0)
            elif date_range_type == '7_days':
                start_date = (yesterday - timedelta(days=6)).replace(hour=0, minute=0, second=0, microsecond=0)
            elif date_range_type == '30_days':
                start_date = (yesterday - timedelta(days=29)).replace(hour=0, minute=0, second=0, microsecond=0)
            else:  # 90_days
                start_date = (yesterday - timedelta(days=89)).replace(hour=0, minute=0, second=0, microsecond=0)
            
            # Generate report
            tm = TemplateManager(api_key_hash)
            template = tm.get_template(schedule['template_id'])
            
            if not template:
                raise ValueError(f"Template {schedule['template_id']} not found")
            
            generator = ReportGenerator(db, user_tz)
            report_html = generator.generate_report(
                template['html_template'],
                start_date,
                end_date,
                client_id=schedule.get('client_id')
            )
            
            # Prepare attachments based on format
            attachments = []
            attachment_format = schedule.get('attachment_format', 'html')
            
            if attachment_format in ['html', 'both']:
                attachments.append({
                    'Name': 'report.html',
                    'Content': report_html,
                    'ContentType': 'text/html'
                })
            
            if attachment_format in ['pdf', 'both']:
                pdf_content = self.pdf_service.html_to_pdf(report_html)
                attachments.append({
                    'Name': 'report.pdf',
                    'Content': pdf_content,
                    'ContentType': 'application/pdf'
                })
            
            # Get report data for email template variables
            report_data = generator.get_report_data(start_date, end_date, schedule.get('client_id'))
            
            # Render email subject and body with template variables
            from jinja2 import Template
            
            subject_template = Template(schedule.get('email_subject', 'Slide Backup Report'))
            email_subject = subject_template.render(**report_data)
            
            body_template = Template(schedule.get('email_body', 'Your report is attached.'))
            email_body = body_template.render(**report_data)
            
            # Send email
            self.email_service.send_email(
                to_email=schedule['email_address'],
                subject=email_subject,
                body=email_body,
                attachments=attachments
            )
            
            # Log successful send
            date_range_str = f"{start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}"
            self._log_email_send(db, schedule['schedule_id'], schedule['email_address'],
                               'success', None, date_range_str)
            
            # Update schedule
            esm.update_after_run(schedule['schedule_id'], True, None, timezone)
            
            logger.info(f"Successfully sent email for schedule {schedule['schedule_id']}")
        
        except Exception as e:
            logger.error(f"Error executing schedule {schedule['schedule_id']}: {e}", exc_info=True)
            
            # Log failed send
            self._log_email_send(db, schedule['schedule_id'], schedule['email_address'],
                               'failed', str(e), None)
            
            # Still update the schedule to prevent repeated failures
            esm.update_after_run(schedule['schedule_id'], False, str(e), timezone)
    
    def _log_email_send(self, db: Database, schedule_id: int, recipient: str,
                       status: str, error_message: str, date_range: str):
        """Log an email send to the database"""
        try:
            with db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO email_send_log
                    (schedule_id, sent_at, status, error_message, recipient_email, report_date_range)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (schedule_id, datetime.utcnow().isoformat(), status,
                      error_message, recipient, date_range))
        except Exception as e:
            logger.error(f"Error logging email send: {e}")


# Global scheduler instance (will be initialized in app.py)
email_scheduler = None

