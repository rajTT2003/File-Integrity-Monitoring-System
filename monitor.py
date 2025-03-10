import sys
import time 
from watchdog.observers import Observer 
from watchdog.events import LoggingEventHandler, PatternMatchingEventHandler
import logging 
import getpass
import shutil
import os

# # To make backup directory
# def on_modified(event):
#     backup_path = r'C:\Users\Rajaire Thomas\Desktop\FIM\Backup\\'

#     # Ensure the backup directory exists
#     os.makedirs(backup_path, exist_ok=True)

#     # Fetching all files in path
#     for file_name in os.listdir(path):
#         # Construct full file paths
#         source = os.path.join(path, file_name)
#         destination = os.path.join(backup_path, file_name)

#         # Copying all files
#         if os.path.isfile(source):
#             shutil.copy(source, destination)
#             print(f'Copied: {file_name}')

class Handler(PatternMatchingEventHandler):
    def __init__(self) -> None:
        PatternMatchingEventHandler.__init__(self, patterns=['*.csv'],
                         ignore_directories=True, case_sensitive=False)
        
    def on_created(self,event):
        print("A new create event was made", event.src_path)
    
    def on_modified(self, event):
        print("A new modified event was made", event.src_path)

    def on_deleted(self, event):
        print("A deleton event was made", event.src_path)

if __name__ == '__main__':
    # Storing logs with particular user
    user = getpass.getuser()

    # Storing to file    
    logging.basicConfig(filename='dev.log', filemode='a',
    level=logging.INFO,
    format='%(asctime)s  | %(process)d  |  %(message)s' + f' | userId:{user}', datefmt='%Y-%m-%d %H:%M:%S'
)

    # Directory to be monitored
    path = sys.argv[1] if len(sys.argv) > 1 else '.'
    
    event_handler = Handler()
    # event_handler.on_modified = on_modified
    observer = Observer()
    observer.schedule(event_handler, path, recursive=True)
    observer.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
        observer.join()
