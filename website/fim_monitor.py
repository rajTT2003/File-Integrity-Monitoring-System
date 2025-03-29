import os
import hashlib
import json
import shutil
import time
import logging
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# Constants
BASELINE_FILE = "baseline.json"
BACKUP_DIR = "Backups"
MONITOR_DIR = "Monitor"
CRITICAL_EXTENSIONS = ['.conf', '.xml', '.json', '.dll']
LOG_FILE = "fim.log"

# Logging Setup
fim_logger = logging.getLogger("FIMLogger")
fim_logger.setLevel(logging.INFO)
file_handler = logging.FileHandler(LOG_FILE)
formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")
file_handler.setFormatter(formatter)
fim_logger.addHandler(file_handler)

def calculate_sha256(file_path):
    """Compute SHA-256 hash of a file."""
    try:
        with open(file_path, "rb") as f:
            sha256 = hashlib.sha256()
            while chunk := f.read(4096):
                sha256.update(chunk)
            return sha256.hexdigest()
    except Exception as e:
        fim_logger.error(f"Error hashing file {file_path}: {e}")
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
                baseline[relative_path] = calculate_sha256(file_path)

    with open(BASELINE_FILE, "w") as f:
        json.dump(baseline, f, indent=4)

    fim_logger.info("Baseline created successfully.")

def load_baseline():
    """Load the existing baseline from JSON."""
    if os.path.exists(BASELINE_FILE):
        with open(BASELINE_FILE, "r") as f:
            return json.load(f)
    return {}

def compare_with_baseline(directory):
    """Compare current state with baseline."""
    baseline = load_baseline()
    current_files = {}

    for root, _, files in os.walk(directory):
        for file in files:
            file_path = os.path.join(root, file)
            if is_critical(file_path):
                relative_path = os.path.relpath(file_path, directory)
                current_files[relative_path] = calculate_sha256(file_path)

    added_files = set(current_files.keys()) - set(baseline.keys())
    deleted_files = set(baseline.keys()) - set(current_files.keys())
    modified_files = [f for f in current_files if f in baseline and baseline[f] != current_files[f]]

    return added_files, deleted_files, modified_files

def create_backup(file_path):
    """Create a backup of a file."""
    if not os.path.exists(file_path):
        fim_logger.warning(f"File not found, cannot back up: {file_path}")
        return

    os.makedirs(BACKUP_DIR, exist_ok=True)
    backup_name = f"{os.path.basename(file_path)}_{time.strftime('%Y-%m-%d_%H-%M-%S')}"
    backup_path = os.path.join(BACKUP_DIR, backup_name)
    shutil.copy2(file_path, backup_path)
    fim_logger.info(f"Backup created for: {file_path}")

def restore_backup(backup_name, user_role):
    """Restore a file from backup (Admins only)."""
    if user_role != "admin":
        fim_logger.warning("Unauthorized restore attempt.")
        return "Permission denied"

    backup_path = os.path.join(BACKUP_DIR, backup_name)
    if os.path.exists(backup_path):
        original_name = backup_name.split("_")[0]
        original_path = os.path.join(MONITOR_DIR, original_name)
        shutil.copy2(backup_path, original_path)
        fim_logger.info(f"File restored from backup: {backup_name}")
        return "File restored successfully"
    else:
        fim_logger.error(f"Backup file {backup_name} not found.")
        return "Backup file not found."

class FIMHandler(FileSystemEventHandler):
    """Watchdog event handler to monitor file changes."""

    def __init__(self, user_role):
        """Initialize with user role since Flask-Login's current_user doesn't work in a separate thread."""
        self.user_role = user_role  

    def on_any_event(self, event):
        """Handle file system events."""
        try:
            added_files, deleted_files, modified_files = compare_with_baseline(MONITOR_DIR)

            for file in added_files:
                if is_critical(file):
                    fim_logger.warning(f"Critical file added: {file}")
                    if self.user_role == "employee":
                        print(f"⚠️ Warning: Critical file added ({file})")
                else:
                    fim_logger.info(f"New file detected: {file}")
                    create_backup(os.path.join(MONITOR_DIR, file))

            for file in deleted_files:
                if is_critical(file):
                    fim_logger.warning(f"Critical file deleted: {file}")
                    if self.user_role == "employee":
                        print(f"⚠️ Warning: Critical file deleted ({file})")
                else:
                    fim_logger.info(f"File deleted: {file}")

            for file in modified_files:
                if is_critical(file):
                    if self.user_role == "admin":
                        create_baseline(MONITOR_DIR)
                        fim_logger.info(f"Admin modified critical file. Baseline updated: {file}")
                    else:
                        fim_logger.warning(f"Critical file modified: {file}")
                        print(f"⚠️ Warning: Critical file modified ({file})")
                else:
                    fim_logger.info(f"File modified: {file}")
                    create_backup(os.path.join(MONITOR_DIR, file))

        except Exception as e:
            fim_logger.error(f"Error processing event: {e}")

def start_fim_monitor(directory, user_role):
    """Start monitoring files with Watchdog."""
    fim_logger.info(f"Starting FIM monitoring on: {directory}")

    if not os.path.exists(BASELINE_FILE):
        create_baseline(directory)

    observer = Observer()
    observer.schedule(FIMHandler(user_role), directory, recursive=True)
    observer.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()
