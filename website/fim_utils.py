# fim_utils.py
import os
import hashlib
import logging

# Logging Setup
fim_logger = logging.getLogger("FIMLogger")
fim_logger.setLevel(logging.INFO)
file_handler = logging.FileHandler("fim.log")
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
        fim_logger.error(f"Hashing failed for {file_path} | {e}")
        return None

def is_critical(file_path):
    """Check if a file is critical based on its extension."""
    CRITICAL_EXTENSIONS = ['.conf', '.xml', '.json', '.dll']
    return os.path.splitext(file_path)[1] in CRITICAL_EXTENSIONS
