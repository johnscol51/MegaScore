import datetime

# Internal variable set by MegaScore
_log_path = None

def init_logger(path):
    """Initialise the logger with a fully qualified log file path."""
    global _log_path
    _log_path = path

def log(message):
    """Write a timestamped message to the log file if initialised."""
    if not _log_path:
        return  # fail silently if logger not initialised

    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        with open(_log_path, "a", encoding="utf-8") as f:
            f.write(f"[{timestamp}] {message}\n")
    except Exception:
        pass  # avoid crashing the app if logging fails

