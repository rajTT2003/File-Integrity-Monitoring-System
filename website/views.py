import os
import shutil  # ✅ Import shutil for deleting non-empty folders
from flask import Blueprint, render_template, jsonify, request, send_from_directory
from flask_login import login_required, current_user
from .fim_monitor import restore_backup
import threading
from .fim_monitor import start_fim_monitor, MONITOR_DIR
from .fim_monitor import is_critical

views = Blueprint('views', __name__)

@views.route('/')
@login_required
def home():
    return render_template("home.html", user=current_user)

@views.route('/fileView')
@login_required
def fileView():
    return render_template('fileView.html', user=current_user)

# Set the ROOT_FOLDER dynamically based on the project structure
BASE_DIR = os.path.abspath(os.path.dirname(__file__))  # Gets the Flask app directory
ROOT_FOLDER = os.path.join(os.path.dirname(BASE_DIR), "Monitor")  # Moves up one level

# --- API Endpoints --- #

@views.route("/api/root")
@login_required  # ✅ Added authentication
def get_root():
    """Returns the root folder path (Monitor) to the frontend"""
    return jsonify({"root": ROOT_FOLDER})

@views.route("/api/list")
@login_required
def list_directory():
    """Lists files and folders inside a given directory"""
    requested_path = request.args.get("path", "").strip()
    abs_path = os.path.normpath(os.path.join(ROOT_FOLDER, *requested_path.split("/")))

    if not abs_path.startswith(ROOT_FOLDER):
        return jsonify({"error": "Access Denied"}), 403

    try:
        items = [{"name": entry.name, "path": os.path.relpath(entry.path, ROOT_FOLDER), "isFolder": entry.is_dir(),"isCritical": is_critical(entry.path)} for entry in os.scandir(abs_path)]
        return jsonify({"files": items})
    except PermissionError:
        return jsonify({"error": "Access Denied"}), 403

@views.route("/api/tree")
@login_required
def get_folder_tree():
    """Returns the hierarchical folder structure starting from ROOT_FOLDER."""
    def build_tree(directory):
        """Recursively builds folder structure."""
        tree = []
        try:
            for entry in os.scandir(directory):
                if entry.is_dir():
                    tree.append({
                        "name": entry.name,
                        "path": os.path.relpath(entry.path, ROOT_FOLDER),
                        "children": build_tree(entry.path)
                    })
        except PermissionError:
            return []  # Return empty if permission is denied
        return tree

    return jsonify(build_tree(ROOT_FOLDER))

@views.route("/api/file")
@login_required
def serve_file():
    """Serves files for viewing"""
    requested_path = request.args.get("path", "").strip()
    abs_path = os.path.normpath(os.path.join(ROOT_FOLDER, *requested_path.split("/")))

    if not abs_path.startswith(ROOT_FOLDER) or not os.path.exists(abs_path):
        return "Not Found", 404

    return send_from_directory(os.path.dirname(abs_path), os.path.basename(abs_path))

# --- File Operations --- #

@views.route("/api/create-file", methods=["POST"])
@login_required
def create_file():
    """Creates a new file in the given directory."""
    data = request.get_json()
    path = data.get("path", "").strip()
    name = data.get("name", "").strip()

    if not name:
        return jsonify({"error": "Invalid file name"}), 400

    file_path = os.path.normpath(os.path.join(ROOT_FOLDER, *path.split("/"), name))

    if not file_path.startswith(ROOT_FOLDER):
        return jsonify({"error": "Access Denied"}), 403

    try:
        with open(file_path, 'w') as f:
            pass  # Create an empty file
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@views.route("/api/create-folder", methods=["POST"])
@login_required
def create_folder():
    """Creates a new folder in the given directory."""
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
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@views.route("/api/edit-item", methods=["POST"])
@login_required
def edit_item():
    """Renames a file or folder"""
    try:
        data = request.get_json()
        relative_path = data.get("path", "").strip()
        new_name = data.get("newName", "").strip()

        if not relative_path or not new_name:
            return jsonify({"error": "Invalid input"}), 400

        abs_path = os.path.normpath(os.path.join(ROOT_FOLDER, relative_path))

        if not abs_path.startswith(ROOT_FOLDER) or not os.path.exists(abs_path):
            return jsonify({"error": "Access Denied or File Not Found"}), 403

        new_path = os.path.normpath(os.path.join(os.path.dirname(abs_path), new_name))

        os.rename(abs_path, new_path)
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@views.route("/api/delete-item", methods=["DELETE"])
@login_required
def delete_item():
    """Deletes a file or folder"""
    try:
        data = request.get_json()
        relative_path = data.get("path", "").strip()

        if not relative_path:
            return jsonify({"error": "Invalid path"}), 400

        abs_path = os.path.normpath(os.path.join(ROOT_FOLDER, relative_path))

        if not abs_path.startswith(ROOT_FOLDER):
            return jsonify({"error": "Access Denied"}), 403

        if not os.path.exists(abs_path):
            return jsonify({"error": "File not found"}), 404

        if os.path.isdir(abs_path):
            shutil.rmtree(abs_path)  # ✅ Use shutil to delete non-empty folders
        else:
            os.remove(abs_path)

        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@views.route('/restore-backup', methods=['POST'])
@login_required
def restore_backup_route():
    if current_user.role != "admin":
        return jsonify({"error": "Permission denied"}), 403
    
    data = request.json
    backup_name = data.get("backup_name")

    if not backup_name:
        return jsonify({"error": "No backup specified"}), 400

    result = restore_backup(backup_name)
    return jsonify({"message": result})




@views.route('/start-monitoring')
@login_required
def start_monitoring():
    """Start File Integrity Monitoring after user login."""
    user_role = current_user.role  # Get the logged-in user's role

    fim_thread = threading.Thread(target=start_fim_monitor, args=(MONITOR_DIR, current_user.role), daemon=True)

    fim_thread.start()

    return jsonify({"message": "FIM monitoring started."})
