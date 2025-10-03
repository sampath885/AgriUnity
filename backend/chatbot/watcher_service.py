# backend/chatbot/watcher_service.py

import time
import os
import threading
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from django.conf import settings
from . import knowledge_base_manager # Import our manager

SUPPORTED_EXTENSIONS = ('.pdf', '.csv')
TEMP_EXTENSIONS = ('.tmp', '.crdownload')

# Debounce registry to avoid duplicate rapid events
_last_processed_at = {}
_debounce_lock = threading.Lock()
_MIN_PROCESS_INTERVAL_SECONDS = 3


def _should_process_file(path: str) -> bool:
    if not path.lower().endswith(SUPPORTED_EXTENSIONS):
        return False
    if path.lower().endswith(TEMP_EXTENSIONS):
        return False

    now = time.time()
    with _debounce_lock:
        last_time = _last_processed_at.get(path)
        if last_time is not None and (now - last_time) < _MIN_PROCESS_INTERVAL_SECONDS:
            return False
        _last_processed_at[path] = now
    return True


class KnowledgeBaseEventHandler(FileSystemEventHandler):
    """Handles file system events in the 'data' directory."""
    def on_created(self, event):
        if not event.is_directory and _should_process_file(event.src_path):
            knowledge_base_manager.sync_file_to_kb(event.src_path)

    def on_modified(self, event):
        if not event.is_directory and _should_process_file(event.src_path):
            knowledge_base_manager.sync_file_to_kb(event.src_path)

    def on_deleted(self, event):
        if not event.is_directory and event.src_path.lower().endswith(SUPPORTED_EXTENSIONS):
            # Delay slightly to confirm it's not an in-progress replace
            def _confirm_and_delete(path: str):
                time.sleep(1.5)
                if not os.path.exists(path):
                    knowledge_base_manager.remove_file_from_kb(path)

            threading.Thread(target=_confirm_and_delete, args=(event.src_path,), daemon=True).start()

def start_watcher():
    """Starts the file system watcher in a background thread."""
    data_path = os.path.join(settings.BASE_DIR, 'data')
    
    # Ensure the data directory exists
    if not os.path.exists(data_path):
        print(f"Watcher: Data directory '{data_path}' not found. Creating it.")
        os.makedirs(data_path)

    print("--- Knowledge Base Watcher Service ---")
    print(f"Watching for file changes in: {data_path}")
    
    event_handler = KnowledgeBaseEventHandler()
    observer = Observer()
    observer.schedule(event_handler, data_path, recursive=False)
    observer.start()
    print("Watcher started successfully.")

    try:
        # The thread will block here until the main process is terminated
        while True:
            time.sleep(60) # Sleep for a minute to reduce CPU usage
    except KeyboardInterrupt:
        observer.stop()
    observer.join()

def run_watcher_in_background():
    """Creates and starts a daemon thread for the watcher."""
    watcher_thread = threading.Thread(target=start_watcher, daemon=True)
    watcher_thread.start()
    print("Knowledge base watcher thread has been started in the background.")