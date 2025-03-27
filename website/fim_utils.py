import os
import hashlib
import json

BASELINE_FILE = "baseline.json"

def calculate_sha256(file_path):
    """Compute SHA-256 hash of a file."""
    try:
        with open(file_path, "rb") as f:
            sha256 = hashlib.sha256()
            while chunk := f.read(4096):
                sha256.update(chunk)
            return sha256.hexdigest()
    except Exception as e:
        print(f"Error hashing file {file_path}: {e}")
        return None

def create_baseline(directory):
    """Scan all files in the directory and store their hashes."""
    baseline = {}

    for root, _, files in os.walk(directory):
        for file in files:
            file_path = os.path.join(root, file)
            relative_path = os.path.relpath(file_path, directory)
            baseline[relative_path] = calculate_sha256(file_path)

    # Save baseline to a JSON file
    with open(BASELINE_FILE, "w") as f:
        json.dump(baseline, f, indent=4)

    print("Baseline created successfully.")

def load_baseline():
    """Load the existing baseline from JSON."""
    if os.path.exists(BASELINE_FILE):
        with open(BASELINE_FILE, "r") as f:
            return json.load(f)
    return {}

def compare_with_baseline(directory):
    """Compare current file hashes with the stored baseline."""
    baseline = load_baseline()
    current_files = {}

    for root, _, files in os.walk(directory):
        for file in files:
            file_path = os.path.join(root, file)
            relative_path = os.path.relpath(file_path, directory)
            current_files[relative_path] = calculate_sha256(file_path)

    added_files = set(current_files.keys()) - set(baseline.keys())
    deleted_files = set(baseline.keys()) - set(current_files.keys())
    modified_files = [f for f in current_files if f in baseline and baseline[f] != current_files[f]]

    return added_files, deleted_files, modified_files
