import os
import time
import logging
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from .fim_utils import compare_with_baseline, create_baseline

LOG_FILE = "fim.log"
BASELINE_FILE = "baseline.json"  # Ensure this is defined

# Define the monitoring directory (replace with actual directory)
MONITOR_DIR = "Monitor"  # <-- Specify your monitoring directory here

# Create a separate logger for FIM
fim_logger = logging.getLogger("FIMLogger")
fim_logger.setLevel(logging.INFO)
file_handler = logging.FileHandler(LOG_FILE)
formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
file_handler.setFormatter(formatter)
fim_logger.addHandler(file_handler)

# Dictionary to track the last event timestamp for debouncing
event_timestamps = {}

# Time threshold for debouncing (in seconds)
DEBOUNCE_THRESHOLD = 1


class FIMHandler(FileSystemEventHandler):
    def on_any_event(self, event):
        """Run baseline comparison whenever a file event occurs."""
        file_path = event.src_path
        current_time = time.time()
        
        # Check if the event is within the debounce threshold
        last_event_time = event_timestamps.get(file_path, 0)
        if current_time - last_event_time < DEBOUNCE_THRESHOLD:
            return  # Skip the event if it's within the debounce threshold
        
        # Update the last event time for the file
        event_timestamps[file_path] = current_time

        added_files, deleted_files, modified_files = compare_with_baseline(MONITOR_DIR)

        if added_files:
            for file in added_files:
                fim_logger.warning(f"New file detected: {file}")

        if deleted_files:
            for file in deleted_files:
                fim_logger.warning(f"File deleted: {file}")

        if modified_files:
            for file in modified_files:
                fim_logger.warning(f"File modified: {file}")


def start_fim_monitor(directory):
    """Starts real-time monitoring using Watchdog and initializes the baseline."""
    fim_logger.info(f"Starting FIM monitoring on: {directory}")
    
    # Ensure baseline exists before monitoring
    if not os.path.exists(BASELINE_FILE):
        create_baseline(directory)
        fim_logger.info("Baseline created successfully.")

    event_handler = FIMHandler()
    observer = Observer()
    observer.schedule(event_handler, directory, recursive=True)
    observer.start()
    
    try:
        while True:
            time.sleep(1)  # Keeps the thread alive and checks for events
    except KeyboardInterrupt:
        observer.stop()
    observer.join()


if __name__ == "__main__":
    start_fim_monitor(MONITOR_DIR)
