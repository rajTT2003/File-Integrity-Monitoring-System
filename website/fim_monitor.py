import os
import hashlib
import json
import shutil
import time
from website.fim_utils import is_critical, fim_logger, calculate_sha256
from website.send_email import send_critical_alert  # Import email function
from flask_login import current_user
import logging
from watchdog.observers import Observer
from collections import defaultdict

# Constants
BASELINE_FILE = "baseline.json"
BACKUP_DIR = "Backups"
MONITOR_DIR = "Monitor"
LOG_FILE = "fim.log"
CRITICAL_EXTENSIONS = ['.conf', '.xml', '.json', '.dll']
user_fim_handlers = {}  # Track FIM handlers per user
ALERT_THRESHOLD = 1  # Max number of file changes before sending a batch email alert
email_batch = defaultdict(list)  # Store alerts for batch processing

# Move the import of FIMHandler inside a function to avoid circular import
def get_fim_handler():
    from website.handler import FIMHandler  # Import inside the function to avoid circular import
    return FIMHandler

def calculate_sha256(file_path):
    """Compute SHA-256 hash of a file."""
    try:
        if os.path.getsize(file_path) == 0:
            fim_logger.warning(f"WARNING | File is empty: {file_path}")
            return None  # Skip empty files
        
        with open(file_path, "rb") as f:
            sha256 = hashlib.sha256()
            while chunk := f.read(4096):
                sha256.update(chunk)
        return sha256.hexdigest()
    except Exception as e:
        fim_logger.error(f"ERROR | Hashing failed for {file_path} | {e}")
        return None

def is_critical(file_path):
    """Check if a file is critical based on its extension."""
    return os.path.splitext(file_path)[1] in CRITICAL_EXTENSIONS

def create_baseline(directory):
    """Create a baseline containing only critical files."""
    baseline = {}
    for root, _, files in os.walk(directory):
        for file in files:
            file_path = os.path.join(root, file)
            if is_critical(file_path):
                relative_path = os.path.relpath(file_path, directory)
                file_hash = calculate_sha256(file_path)  # Ensure hash is calculated

                if file_hash:  # Only add the file if it has a valid hash
                    baseline[relative_path] = file_hash
                else:
                    fim_logger.warning(f"Skipping file with invalid hash: {file_path}")

    with open(BASELINE_FILE, "w") as f:
        json.dump(baseline, f, indent=4)

    fim_logger.info("INFO | Baseline created successfully.")



def load_baseline():
    """Load the existing baseline from JSON."""
    if os.path.exists(BASELINE_FILE):
        with open(BASELINE_FILE, "r") as f:
            return json.load(f)
    return {}

def update_baseline(user_role):
    """Update baseline when admin makes changes."""
    if user_role == "admin":
        fim_logger.info("🛠 Admin is updating the baseline...")
        create_baseline(MONITOR_DIR)

        # 🚨 **Force reload baseline after update**
        global baseline
        baseline = load_baseline()

        fim_logger.info("✅ Baseline updated successfully by admin.")

def compare_with_baseline(directory, recipients):
    """Compare current state with baseline and send email alerts if discrepancies are found."""
    baseline = load_baseline()
    current_files = {}

    for root, _, files in os.walk(directory):
        for file in files:
            file_path = os.path.join(root, file)
            relative_path = os.path.relpath(file_path, directory)

            if is_critical(file_path):
                current_files[relative_path] = calculate_sha256(file_path)

    added_files = set(current_files.keys()) - set(baseline.keys())
    deleted_files = set(baseline.keys()) - set(current_files.keys())
    modified_files = [f for f in current_files if f in baseline and baseline[f] != current_files[f]]

    # 🚨 **Detect unauthorized files that should NOT be in monitored directories**
    unauthorized_files = [f for f in added_files if not is_critical(os.path.join(directory, f))]

    # Check if there are discrepancies to alert
    if added_files or deleted_files or modified_files or unauthorized_files:
        fim_logger.warning("🚨 Baseline mismatch detected!")

        # Accumulate changes for batch email alert if the threshold is exceeded
        email_batch[recipients].append({
            "added": list(added_files),
            "deleted": list(deleted_files),
            "modified": list(modified_files),
            "unauthorized": list(unauthorized_files)
        })

        # If batch reaches the threshold, send the email and reset the batch
        if len(email_batch[recipients]) >= ALERT_THRESHOLD:
            fim_logger.info(f"Sending batch email alert for {recipients}")
            send_batch_email_alert(recipients)
            email_batch[recipients] = []  # Reset batch after sending

    return added_files, deleted_files, modified_files, unauthorized_files

def send_batch_email_alert(recipients):
    """Send a batch email alert to admins."""
    all_added_files = []
    all_deleted_files = []
    all_modified_files = []
    all_unauthorized_files = []

    for alert in email_batch[recipients]:
        all_added_files.extend(alert['added'])
        all_deleted_files.extend(alert['deleted'])
        all_modified_files.extend(alert['modified'])
        all_unauthorized_files.extend(alert['unauthorized'])

    send_critical_alert(
        recipients=recipients,
        added_files=all_added_files,
        deleted_files=all_deleted_files,
        modified_files=all_modified_files,
        unauthorized_files=all_unauthorized_files
    )
    fim_logger.info(f"Batch email sent to {recipients}")

def create_backup(file_path):
    """Create a backup of a file."""
    if not os.path.exists(file_path):
        fim_logger.warning(f"WARNING | File not found, cannot back up: {file_path}")
        return

    os.makedirs(BACKUP_DIR, exist_ok=True)
    timestamp = time.strftime('%Y-%m-%d_%H-%M-%S')
    backup_name = f"{os.path.basename(file_path)}_{timestamp}"
    backup_path = os.path.join(BACKUP_DIR, backup_name)
    shutil.copy2(file_path, backup_path)
    fim_logger.info(f"INFO | Backup created for: {file_path}")

def restore_backup(backup_name, user_role):
    """Restore a file from backup (Admins only)."""
    if user_role != "admin":
        fim_logger.warning("WARNING | Unauthorized restore attempt.")
        return "Permission denied"

    backup_path = os.path.join(BACKUP_DIR, backup_name)
    if os.path.exists(backup_path):
        original_name = "_".join(backup_name.split("_")[:-1])  # Extract original name without timestamp
        original_path = os.path.join(MONITOR_DIR, original_name)
        shutil.copy2(backup_path, original_path)
        fim_logger.info(f"INFO | File restored from backup: {backup_name}")
        return "File restored successfully"
    else:
        fim_logger.error(f"ERROR | Backup file {backup_name} not found.")
        return "Backup file not found."

def start_fim_monitor(directory, user_role, username):
    """Start monitoring files with Watchdog and create backups for all critical files."""
    fim_logger.info(f"INFO | Starting FIM monitoring on: {directory}")

    # Create backups for all critical files before starting monitoring
    for root, _, files in os.walk(directory):
        for file in files:
            file_path = os.path.join(root, file)
            if is_critical(file_path):
                create_backup(file_path)  # Create backup for each critical file

    # Create baseline if it does not exist
    if not os.path.exists(BASELINE_FILE):
        create_baseline(directory)

    # Avoid duplicate monitoring for the same user
    if username in user_fim_handlers:
        fim_logger.warning(f"WARNING | FIM monitoring already running for {username}")
        return

    # Create the correct handler for each role
    fim_handler = get_fim_handler()(user_role, username)  # Use the function to get FIMHandler

    # Ensure the observer is created with the correct handler
    observer = Observer()
    observer.schedule(fim_handler, directory, recursive=True)
    observer.start()

    # Keep track of the observer for each user
    user_fim_handlers[username] = observer

    try:
        observer.join()
    except KeyboardInterrupt:
        observer.stop()
    observer.join()
