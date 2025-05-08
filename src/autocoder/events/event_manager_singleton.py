
import threading
import os
import time
import glob
from typing import Optional
from loguru import logger

from .event_manager import EventManager
from autocoder.common import AutoCoderConfig # Moved import to top

# Constants for the cleanup thread
CLEANUP_INTERVAL_SECONDS = 3600  # 1 hour
MAX_EVENT_FILES_TO_KEEP = 100
EVENT_FILE_PATTERN = "*.jsonl"  # Pattern to match event files, e.g., all .jsonl files

def _cleanup_event_files(event_dir: str):
    """
    Cleans up old event files in the specified directory.
    Keeps only the MAX_EVENT_FILES_TO_KEEP newest files based on filename sorting.
    Assumes filenames are structured to be chronologically sortable (e.g., timestamp-prefixed).
    """
    logger.info(f"Starting cleanup of event files in directory: {event_dir}")
    try:
        if not os.path.isdir(event_dir):
            logger.warning(f"Event directory {event_dir} does not exist. Skipping cleanup.")
            return

        file_pattern = os.path.join(event_dir, EVENT_FILE_PATTERN)
        event_files = glob.glob(file_pattern)

        if not event_files:
            logger.info(f"No event files found matching pattern '{file_pattern}' in directory '{event_dir}'.")
            return

        # Sort files. Assumes filenames allow chronological sorting (e.g., 'YYYYMMDDHHMMSS_event.jsonl').
        # Sorts in ascending order (oldest first).
        event_files.sort()

        if len(event_files) > MAX_EVENT_FILES_TO_KEEP:
            files_to_delete_count = len(event_files) - MAX_EVENT_FILES_TO_KEEP
            files_to_delete = event_files[:files_to_delete_count]  # Oldest files

            logger.info(f"Found {len(event_files)} event files. Will delete {files_to_delete_count} oldest files to keep {MAX_EVENT_FILES_TO_KEEP}.")
            for f_path in files_to_delete:
                try:
                    os.remove(f_path)
                    logger.info(f"Deleted old event file: {f_path}")
                except OSError as e:
                    logger.error(f"Error deleting event file {f_path}: {str(e)}")
                    logger.exception(e) # Log full stack trace for OSError
        else:
            logger.info(f"Found {len(event_files)} event files. No cleanup needed as it's within the limit of {MAX_EVENT_FILES_TO_KEEP}.")

    except Exception as e:
        logger.error(f"An unexpected error occurred during event file cleanup in {event_dir}: {str(e)}")
        logger.exception(e) # Log full stack trace for any other exception

def _event_cleanup_thread_target(event_dir: str, stop_event: threading.Event):
    """
    Target function for the background thread that periodically cleans up event files.
    """
    logger.info(f"Event cleanup thread started for directory: {event_dir}. Interval: {CLEANUP_INTERVAL_SECONDS}s, Max files: {MAX_EVENT_FILES_TO_KEEP}.")
    while not stop_event.is_set():
        _cleanup_event_files(event_dir)
        # Wait for the interval or until stop_event is set
        # This makes the thread responsive to the stop_event even during the wait
        stop_event.wait(timeout=CLEANUP_INTERVAL_SECONDS)
    logger.info(f"Event cleanup thread for directory {event_dir} is stopping.")


class EventManagerSingleton:
    _instance: Optional['EventManagerSingleton'] = None
    _lock = threading.Lock()
    _manager: Optional[EventManager] = None
    
    # Attributes for the cleanup thread
    _cleanup_thread: Optional[threading.Thread] = None
    _stop_cleanup_event: Optional[threading.Event] = None

    def __init__(self):
        # Singleton pattern: __init__ should not be called directly.
        # Initialization logic is in get_instance.
        if EventManagerSingleton._instance is not None:
            raise RuntimeError("Singleton already initialized. Use get_instance().")

    @classmethod
    def get_instance(cls) -> EventManager:
        if cls._instance is None: # First check (no lock)
            with cls._lock: # Second check (with lock)
                if cls._instance is None:
                    cls._instance = cls.__new__(cls) # Create instance without calling __init__ directly again
                    
                    config = AutoCoderConfig.get_instance()
                    event_store_path = config.EVENT_STORE_PATH
                    cls._manager = EventManager(event_store_path=event_store_path)
                    logger.info(f"EventManager initialized with event store path: {event_store_path}")

                    # Start cleanup thread
                    event_dir = os.path.dirname(os.path.abspath(event_store_path))
                    
                    cls._stop_cleanup_event = threading.Event()
                    cls._cleanup_thread = threading.Thread(
                        target=_event_cleanup_thread_target,
                        args=(event_dir, cls._stop_cleanup_event),
                        daemon=True  # Daemon threads exit when the main program exits
                    )
                    cls._cleanup_thread.start()
                    # Logger message for thread start is in _event_cleanup_thread_target
                                        
        if cls._manager is None:
            # This case should ideally not be reached if initialization logic is correct
            raise RuntimeError("EventManager (_manager) not initialized properly within singleton.")
        return cls._manager

    @classmethod
    def get_manager(cls) -> Optional[EventManager]:
        """Returns the managed EventManager instance, or None if not initialized."""
        return cls._manager

    @classmethod
    def shutdown(cls):
        """Shuts down the EventManagerSingleton, including the event cleanup thread and event store."""
        with cls._lock:
            logger.info("Attempting to shut down EventManagerSingleton...")
            if cls._stop_cleanup_event:
                logger.info("Signaling event cleanup thread to stop...")
                cls._stop_cleanup_event.set()
            
            if cls._cleanup_thread and cls._cleanup_thread.is_alive():
                logger.info(f"Waiting for event cleanup thread ({cls._cleanup_thread.name}) to join...")
                cls._cleanup_thread.join(timeout=5.0)  # Wait for thread to finish
                if cls._cleanup_thread.is_alive():
                    logger.warning("Event cleanup thread did not stop in time.")
                else:
                    logger.info("Event cleanup thread stopped.")
            
            if cls._manager and hasattr(cls._manager, 'event_store') and hasattr(cls._manager.event_store, 'close'):
                try:
                    logger.info("Closing event store...")
                    cls._manager.event_store.close() # type: ignore
                    logger.info("Event store closed.")
                except Exception as e:
                    logger.error(f"Error closing event store: {str(e)}")
                    logger.exception(e)
            
            # Reset singleton state
            cls._instance = None
            cls._manager = None
            cls._cleanup_thread = None
            cls._stop_cleanup_event = None
            logger.info("EventManagerSingleton shutdown complete and reset.")

    @classmethod
    def clear(cls):
        """
        Clears the singleton instance and its manager.
        Primarily for testing or re-initialization scenarios.
        For graceful shutdown of resources, prefer shutdown().
        """
        logger.warning("Calling EventManagerSingleton.clear(). For resource cleanup, prefer shutdown().")
        with cls._lock:
            if cls._manager and hasattr(cls._manager, 'event_store') and hasattr(cls._manager.event_store, 'close'):
                # Minimal cleanup, actual resource release should be in shutdown
                try:
                    cls._manager.event_store.close() # type: ignore
                except Exception: # nosec
                    pass # Suppress errors during clear, focus is on state reset
            
            cls._instance = None
            cls._manager = None
            # Note: This does not actively stop the cleanup thread if it was started.
            # For full cleanup including thread, shutdown() must be called.
            cls._cleanup_thread = None 
            cls._stop_cleanup_event = None
            logger.info("EventManagerSingleton cleared (instance and manager references removed).")

