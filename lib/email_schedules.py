"""
Email schedule management for automated report sending.
"""
import sqlite3
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from contextlib import contextmanager
import pytz


class EmailScheduleManager:
    """Manage email schedules for a specific user"""
    
    def __init__(self, db_path: str):
        """
        Initialize email schedule manager.
        
        Args:
            db_path: Path to the SQLite database file
        """
        self.db_path = db_path
    
    @contextmanager
    def get_connection(self):
        """Context manager for database connections"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
    
    def create_schedule(self, name: str, email_address: str, template_id: int,
                       date_range_type: str, client_id: Optional[str] = None,
                       attachment_format: str = 'html',
                       email_subject: Optional[str] = None,
                       email_body: Optional[str] = None,
                       schedule_frequency: Optional[str] = None,
                       schedule_time: Optional[str] = None,
                       schedule_day_of_week: Optional[int] = None,
                       schedule_day_of_month: Optional[int] = None,
                       timezone: str = 'America/New_York') -> int:
        """
        Create a new email schedule.
        
        Args:
            name: User-friendly name for the schedule
            email_address: Recipient email address
            template_id: ID of the template to use
            date_range_type: One of: last_day, 7_days, 30_days, 90_days
            client_id: Optional client filter
            attachment_format: Format for attachments: 'html', 'pdf', or 'both'
            email_subject: Custom email subject (supports template variables)
            email_body: Custom email body (supports template variables)
            schedule_frequency: One of: 'daily', 'weekly', 'monthly', or None for manual-only
            schedule_time: Time in HH:MM format (24-hour)
            schedule_day_of_week: Day of week (0=Monday, 6=Sunday) for weekly schedules
            schedule_day_of_month: Day of month (1-31) for monthly schedules
            timezone: User's timezone for scheduling
            
        Returns:
            schedule_id: ID of the created schedule
        """
        # Set defaults if not provided
        if email_subject is None:
            email_subject = "Slide Backup Report - {{ date_range }}"
        
        if email_body is None:
            email_body = """Your Slide Backup Report for {{ date_range }} is ready.

Executive Summary:
{{ exec_summary }}

Key Metrics:
- Total Backups: {{ total_backups }}
- Success Rate: {{ success_rate }}%

Report generated at {{ generated_at }} ({{ timezone }})"""
        
        # Calculate next_run_at if scheduling is enabled
        next_run_at = None
        if schedule_frequency and schedule_time:
            next_run_at = self.calculate_next_run(
                schedule_frequency, schedule_time, 
                schedule_day_of_week, schedule_day_of_month, timezone
            )
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            now = datetime.utcnow().isoformat()
            cursor.execute("""
                INSERT INTO email_schedules 
                (name, email_address, template_id, date_range_type, client_id, enabled, 
                 attachment_format, email_subject, email_body, schedule_frequency, schedule_time,
                 schedule_day_of_week, schedule_day_of_month, next_run_at, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, 1, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (name, email_address, template_id, date_range_type, client_id, 
                  attachment_format, email_subject, email_body, schedule_frequency, schedule_time,
                  schedule_day_of_week, schedule_day_of_month, next_run_at, now, now))
            return cursor.lastrowid
    
    def get_schedule(self, schedule_id: int) -> Optional[Dict[str, Any]]:
        """
        Get a specific email schedule.
        
        Args:
            schedule_id: ID of the schedule
            
        Returns:
            Schedule dict or None if not found
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM email_schedules WHERE schedule_id = ?", (schedule_id,))
            row = cursor.fetchone()
            if row:
                return dict(row)
            return None
    
    def list_schedules(self) -> List[Dict[str, Any]]:
        """
        List all email schedules.
        
        Returns:
            List of schedule dicts
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM email_schedules ORDER BY created_at DESC")
            return [dict(row) for row in cursor.fetchall()]
    
    def update_schedule(self, schedule_id: int, name: Optional[str] = None,
                       email_address: Optional[str] = None, template_id: Optional[int] = None,
                       date_range_type: Optional[str] = None, client_id: Optional[str] = None,
                       enabled: Optional[bool] = None, attachment_format: Optional[str] = None,
                       email_subject: Optional[str] = None, email_body: Optional[str] = None,
                       schedule_frequency: Optional[str] = None,
                       schedule_time: Optional[str] = None,
                       schedule_day_of_week: Optional[int] = None,
                       schedule_day_of_month: Optional[int] = None,
                       timezone: Optional[str] = None,
                       recalculate_next_run: bool = False):
        """
        Update an email schedule.
        
        Args:
            schedule_id: ID of the schedule to update
            name: New name (optional)
            email_address: New email address (optional)
            template_id: New template ID (optional)
            date_range_type: New date range type (optional)
            client_id: New client ID (optional)
            enabled: New enabled status (optional)
            attachment_format: New attachment format (optional)
            email_subject: New email subject (optional)
            email_body: New email body (optional)
            schedule_frequency: New frequency (optional)
            schedule_time: New time (optional)
            schedule_day_of_week: New day of week (optional)
            schedule_day_of_month: New day of month (optional)
            timezone: Timezone for recalculation (optional)
            recalculate_next_run: If True, recalculate next_run_at based on current schedule
        """
        updates = []
        params = []
        
        if name is not None:
            updates.append("name = ?")
            params.append(name)
        
        if email_address is not None:
            updates.append("email_address = ?")
            params.append(email_address)
        
        if template_id is not None:
            updates.append("template_id = ?")
            params.append(template_id)
        
        if date_range_type is not None:
            updates.append("date_range_type = ?")
            params.append(date_range_type)
        
        if client_id is not None:
            updates.append("client_id = ?")
            params.append(client_id)
        
        if enabled is not None:
            updates.append("enabled = ?")
            params.append(1 if enabled else 0)
        
        if attachment_format is not None:
            updates.append("attachment_format = ?")
            params.append(attachment_format)
        
        if email_subject is not None:
            updates.append("email_subject = ?")
            params.append(email_subject)
        
        if email_body is not None:
            updates.append("email_body = ?")
            params.append(email_body)
        
        if schedule_frequency is not None:
            updates.append("schedule_frequency = ?")
            params.append(schedule_frequency)
        
        if schedule_time is not None:
            updates.append("schedule_time = ?")
            params.append(schedule_time)
        
        if schedule_day_of_week is not None:
            updates.append("schedule_day_of_week = ?")
            params.append(schedule_day_of_week)
        
        if schedule_day_of_month is not None:
            updates.append("schedule_day_of_month = ?")
            params.append(schedule_day_of_month)
        
        # Recalculate next_run_at if requested or if scheduling parameters changed
        if recalculate_next_run or any(x is not None for x in [schedule_frequency, schedule_time, schedule_day_of_week, schedule_day_of_month]):
            schedule = self.get_schedule(schedule_id)
            if schedule:
                freq = schedule_frequency if schedule_frequency is not None else schedule.get('schedule_frequency')
                time = schedule_time if schedule_time is not None else schedule.get('schedule_time')
                dow = schedule_day_of_week if schedule_day_of_week is not None else schedule.get('schedule_day_of_week')
                dom = schedule_day_of_month if schedule_day_of_month is not None else schedule.get('schedule_day_of_month')
                tz = timezone if timezone else 'America/New_York'
                
                if freq and time:
                    next_run = self.calculate_next_run(freq, time, dow, dom, tz)
                    updates.append("next_run_at = ?")
                    params.append(next_run)
        
        updates.append("updated_at = ?")
        params.append(datetime.utcnow().isoformat())
        
        params.append(schedule_id)
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(f"""
                UPDATE email_schedules 
                SET {', '.join(updates)}
                WHERE schedule_id = ?
            """, params)
    
    def delete_schedule(self, schedule_id: int):
        """
        Delete an email schedule.
        
        Args:
            schedule_id: ID of the schedule to delete
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM email_schedules WHERE schedule_id = ?", (schedule_id,))
    
    def toggle_enabled(self, schedule_id: int, enabled: bool):
        """
        Toggle the enabled status of a schedule.
        
        Args:
            schedule_id: ID of the schedule
            enabled: New enabled status
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE email_schedules 
                SET enabled = ?, updated_at = ?
                WHERE schedule_id = ?
            """, (1 if enabled else 0, datetime.utcnow().isoformat(), schedule_id))
    
    def calculate_next_run(self, frequency: str, time_str: str, 
                          day_of_week: Optional[int] = None,
                          day_of_month: Optional[int] = None,
                          timezone: str = 'America/New_York') -> str:
        """
        Calculate the next run time for a schedule.
        
        Args:
            frequency: 'daily', 'weekly', or 'monthly'
            time_str: Time in HH:MM format (24-hour)
            day_of_week: Day of week (0=Monday, 6=Sunday) for weekly schedules
            day_of_month: Day of month (1-31) for monthly schedules
            timezone: User's timezone
            
        Returns:
            ISO timestamp string for next run
        """
        tz = pytz.timezone(timezone)
        now = datetime.now(tz)
        
        # Parse the time
        hour, minute = map(int, time_str.split(':'))
        
        if frequency == 'daily':
            # Schedule for today at the specified time
            next_run = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
            
            # If that time has passed, schedule for tomorrow
            if next_run <= now:
                next_run = next_run + timedelta(days=1)
        
        elif frequency == 'weekly':
            # Schedule for the specified day of week at the specified time
            if day_of_week is None:
                day_of_week = 0  # Default to Monday
            
            # Calculate days until the target day
            days_ahead = day_of_week - now.weekday()
            if days_ahead < 0:
                days_ahead += 7
            elif days_ahead == 0:
                # It's the target day - check if time has passed
                target_time = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
                if target_time <= now:
                    days_ahead = 7
            
            next_run = now.replace(hour=hour, minute=minute, second=0, microsecond=0) + timedelta(days=days_ahead)
        
        elif frequency == 'monthly':
            # Schedule for the specified day of month at the specified time
            if day_of_month is None:
                day_of_month = 1  # Default to first day of month
            
            # Try current month first
            try:
                next_run = now.replace(day=day_of_month, hour=hour, minute=minute, second=0, microsecond=0)
                if next_run <= now:
                    # Move to next month
                    if now.month == 12:
                        next_run = next_run.replace(year=now.year + 1, month=1)
                    else:
                        next_run = next_run.replace(month=now.month + 1)
            except ValueError:
                # Day doesn't exist in current month (e.g., Feb 30)
                # Move to next month and try again
                if now.month == 12:
                    next_month = now.replace(year=now.year + 1, month=1, day=1)
                else:
                    next_month = now.replace(month=now.month + 1, day=1)
                
                # Find the last valid day of the month if day_of_month is too large
                import calendar
                last_day = calendar.monthrange(next_month.year, next_month.month)[1]
                actual_day = min(day_of_month, last_day)
                next_run = next_month.replace(day=actual_day, hour=hour, minute=minute, second=0, microsecond=0)
        
        else:
            raise ValueError(f"Invalid frequency: {frequency}")
        
        # Convert to UTC for storage
        next_run_utc = next_run.astimezone(pytz.UTC)
        return next_run_utc.isoformat()
    
    def get_schedules_due(self) -> List[Dict[str, Any]]:
        """
        Get all schedules that are due to run.
        
        Returns:
            List of schedule dicts that should be executed now
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            now = datetime.utcnow().isoformat()
            cursor.execute("""
                SELECT * FROM email_schedules 
                WHERE enabled = 1 
                AND next_run_at IS NOT NULL 
                AND next_run_at <= ?
                ORDER BY next_run_at
            """, (now,))
            return [dict(row) for row in cursor.fetchall()]
    
    def update_after_run(self, schedule_id: int, success: bool, 
                        error_message: Optional[str] = None,
                        timezone: str = 'America/New_York'):
        """
        Update a schedule after execution.
        
        Args:
            schedule_id: ID of the schedule
            success: Whether the execution was successful
            error_message: Error message if failed
            timezone: User's timezone for recalculating next run
        """
        schedule = self.get_schedule(schedule_id)
        if not schedule:
            return
        
        now = datetime.utcnow().isoformat()
        
        # Calculate next run time
        next_run_at = None
        if schedule.get('schedule_frequency') and schedule.get('schedule_time'):
            next_run_at = self.calculate_next_run(
                schedule['schedule_frequency'],
                schedule['schedule_time'],
                schedule.get('schedule_day_of_week'),
                schedule.get('schedule_day_of_month'),
                timezone
            )
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE email_schedules 
                SET last_run_at = ?, next_run_at = ?, updated_at = ?
                WHERE schedule_id = ?
            """, (now, next_run_at, now, schedule_id))

