from flask import Blueprint, render_template, request, jsonify, send_from_directory
from flask_login import login_required, current_user
import os
import shutil
import threading
import logging
from watchdog.events import FileCreatedEvent, FileDeletedEvent, FileMovedEvent, DirCreatedEvent
from .fim_monitor import is_critical, restore_backup, fim_logger, user_fim_handlers,start_fim_monitor
# In views.py
from .handler import FIMHandler

views = Blueprint('views', __name__)

# Set the ROOT_FOLDER dynamically
BASE_DIR = os.path.abspath(os.path.dirname(__file__))  # Gets the Flask app directory
ROOT_FOLDER = os.path.join(os.path.dirname(BASE_DIR), "Monitor")  # Moves up one level

# Setup logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# --- Routes for rendering pages ---
@views.route('/')
@login_required
def home():
    return render_template("home.html", user=current_user)

@views.route('/fileView')
@login_required
def fileView():
    return render_template('fileView.html', user=current_user)

# --- API Endpoints ---
@views.route("/api/root")
@login_required
def get_root():
    return jsonify({"root": ROOT_FOLDER})

@views.route("/api/list")
@login_required
def list_directory():
    requested_path = request.args.get("path", "").strip()
    abs_path = os.path.normpath(os.path.join(ROOT_FOLDER, *requested_path.split("/")))

    if not abs_path.startswith(ROOT_FOLDER):
        return jsonify({"error": "Access Denied"}), 403

    try:
        items = [
            {
                "name": entry.name,
                "path": os.path.relpath(entry.path, ROOT_FOLDER),
                "isFolder": entry.is_dir(),
                "isCritical": is_critical(entry.path),
            }
            for entry in os.scandir(abs_path)
        ]
        return jsonify({"files": items})
    except PermissionError:
        return jsonify({"error": "Access Denied"}), 403

@views.route("/api/tree")
@login_required
def get_folder_tree():
    def build_tree(directory):
        tree = []
        try:
            for entry in os.scandir(directory):
                if entry.is_dir():
                    tree.append({
                        "name": entry.name,
                        "path": os.path.relpath(entry.path, ROOT_FOLDER),
                        "children": build_tree(entry.path),
                    })
        except PermissionError:
            return []
        return tree

    return jsonify(build_tree(ROOT_FOLDER))

@views.route("/api/file")
@login_required
def serve_file():
    requested_path = request.args.get("path", "").strip()
    abs_path = os.path.normpath(os.path.join(ROOT_FOLDER, *requested_path.split("/")))

    if not abs_path.startswith(ROOT_FOLDER) or not os.path.exists(abs_path):
        return "Not Found", 404

    return send_from_directory(os.path.dirname(abs_path), os.path.basename(abs_path))

# --- File Operations ---
from watchdog.events import FileCreatedEvent, FileDeletedEvent, DirCreatedEvent, FileMovedEvent

def get_fim_handler():
    """Retrieve the FIM handler for the current user."""
    return user_fim_handlers.get(current_user.firstName, FIMHandler(current_user.role, current_user.firstName))


@views.route("/api/create-file", methods=["POST"])
@login_required
def create_file():
    """Creates a new file."""
    data = request.get_json()
    path = data.get("path", "").strip()
    name = data.get("name", "").strip()

    if not name:
        return jsonify({"error": "Invalid file name"}), 400

    file_path = os.path.normpath(os.path.join(ROOT_FOLDER, *path.split("/"), name))
    if not file_path.startswith(ROOT_FOLDER):
        return jsonify({"error": "Access Denied"}), 403

    try:
        with open(file_path, 'w'):
            pass  # Create an empty file

        # Correct event type
        event = FileCreatedEvent(file_path)
        get_fim_handler().on_any_event(event)

        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@views.route("/api/delete-item", methods=["DELETE"])
@login_required
def delete_item():
    """Deletes a file or folder."""
    data = request.get_json()
    relative_path = data.get("path", "").strip()

    if not relative_path:
        return jsonify({"error": "Invalid path"}), 400

    abs_path = os.path.normpath(os.path.join(ROOT_FOLDER, relative_path))
    if not abs_path.startswith(ROOT_FOLDER):
        return jsonify({"error": "Access Denied"}), 403

    if not os.path.exists(abs_path):
        return jsonify({"error": "File not found"}), 404

    try:
        if os.path.isdir(abs_path):
            shutil.rmtree(abs_path)
        else:
            os.remove(abs_path)

        # Correct event type
        event = FileDeletedEvent(abs_path)
        get_fim_handler().on_any_event(event)

        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@views.route("/api/create-folder", methods=["POST"])
@login_required
def create_folder():
    """Creates a new folder."""
    data = request.get_json()
    path = data.get("path", "").strip()
    name = data.get("name", "").strip()

    if not name:
        return jsonify({"error": "Invalid folder name"}), 400

    folder_path = os.path.normpath(os.path.join(ROOT_FOLDER, *path.split("/"), name))
    if not folder_path.startswith(ROOT_FOLDER):
        return jsonify({"error": "Access Denied"}), 403

    try:
        os.makedirs(folder_path, exist_ok=True)

        # Correct event type
        event = DirCreatedEvent(folder_path)
        get_fim_handler().on_any_event(event)

        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@views.route("/api/edit-item", methods=["POST"])
@login_required
def edit_item():
    """Renames a file or folder."""
    data = request.get_json()
    relative_path = data.get("path", "").strip()
    new_name = data.get("newName", "").strip()

    if not relative_path or not new_name:
        return jsonify({"error": "Invalid input"}), 400

    abs_path = os.path.normpath(os.path.join(ROOT_FOLDER, relative_path))
    if not abs_path.startswith(ROOT_FOLDER):
        return jsonify({"error": "Access Denied"}), 403

    if not os.path.exists(abs_path):
        return jsonify({"error": "File Not Found"}), 404

    new_path = os.path.normpath(os.path.join(os.path.dirname(abs_path), new_name))
    if not new_path.startswith(ROOT_FOLDER):
        return jsonify({"error": "Access Denied"}), 403

    try:
        os.rename(abs_path, new_path)

        # Correct event type
        event = FileMovedEvent(abs_path, new_path)
        get_fim_handler().on_any_event(event)

        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500



@views.route('/start-monitoring')
@login_required
def start_monitoring():
    """Start File Integrity Monitoring."""
    username = current_user.firstName

    if username in user_fim_handlers:
        return jsonify({"message": "FIM monitoring already running."}), 400

    fim_thread = threading.Thread(target=start_fim_monitor, args=(ROOT_FOLDER, current_user.role, username), daemon=True)
    fim_thread.start()
    fim_logger.info(f"FIM monitoring started for {username}")

    return jsonify({"message": "FIM monitoring started."})


@views.route('/stop-monitoring')
@login_required
def stop_monitoring():
    """Stop File Integrity Monitoring."""
    username = current_user.firstName
    if username in user_fim_handlers:
        observer = user_fim_handlers[username].observer
        observer.stop()
        observer.join()
        del user_fim_handlers[username]
        fim_logger.info(f"Stopped FIM monitoring for {username}")
        return jsonify({"message": "FIM monitoring stopped."})
    
    return jsonify({"message": "No active monitoring session."}), 400

@views.route("/logs")
@login_required
def get_logs():
    try:
        with open("fim.log", "r") as log_file:
            logs = log_file.read()
        return logs, 200, {"Content-Type": "text/plain"}
    except Exception as e:
        return str(e), 500

