from watchdog.events import FileSystemEventHandler, FileSystemEvent
from website.fim_utils import fim_logger, is_critical
from website.send_email import send_critical_alert  # Assuming send_critical_alert is already defined
from website.models import User  # Assuming you have a User model with a 'role' field in your ORM
from website import db  # Assuming 'db' is the SQLAlchemy instance

import os
import time

MONITOR_DIR = "Monitor"  # Directory to monitor

class FIMHandler(FileSystemEventHandler):
    """Watchdog event handler to monitor file changes."""
    def __init__(self, user_role, username):
        self.user_role = user_role
        self.username = username
        self.added_files = []
        self.deleted_files = []
        self.modified_files = []

    def get_admin_emails(self):
        """Retrieve all admin email addresses from the database."""
        # Query the database for all users with role 'admin'
        admins = User.query.filter_by(role="admin").all()
        return [admin.email for admin in admins]  # Return a list of admin emails

    def on_any_event(self, event):
        """Handle file system events."""
        if not isinstance(event, FileSystemEvent):
            return

        relative_path = os.path.relpath(event.src_path, MONITOR_DIR)
        fim_logger.info(f"{time.strftime('%Y-%m-%d %H:%M:%S')} | INFO | {self.username} ({self.user_role}) triggered {event.event_type} on {relative_path}")

        # Handle added files
        if event.event_type == "created":
            if is_critical(event.src_path):
                self.added_files.append(relative_path)
                fim_logger.info(f"{time.strftime('%Y-%m-%d %H:%M:%S')} | INFO | Critical file added: {relative_path}")
        
        # Handle deleted files
        elif event.event_type == "deleted":
            if is_critical(event.src_path):
                self.deleted_files.append(relative_path)
                fim_logger.info(f"{time.strftime('%Y-%m-%d %H:%M:%S')} | INFO | Critical file deleted: {relative_path}")
        
        # Handle modified files
        elif event.event_type == "modified":
            if is_critical(event.src_path):
                self.modified_files.append(relative_path)
                fim_logger.info(f"{time.strftime('%Y-%m-%d %H:%M:%S')} | INFO | Critical file modified: {relative_path}")

        # If it's a critical file access by non-admin, send the email alert
        if is_critical(event.src_path) and self.user_role != "admin":
            fim_logger.warning(f"{time.strftime('%Y-%m-%d %H:%M:%S')} | WARNING | Unauthorized critical file {event.event_type} by {self.username}: {relative_path}")

            # Get the list of admin emails
            admin_emails = self.get_admin_emails()

            # Send email alert with the accumulated lists of modified, added, and deleted files
            send_critical_alert(
                recipients=admin_emails,  # Get all admin emails dynamically
                added_files=self.added_files,
                deleted_files=self.deleted_files,
                modified_files=self.modified_files
            )
