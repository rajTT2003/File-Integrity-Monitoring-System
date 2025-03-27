import os
from flask import Blueprint, render_template, jsonify, request, send_from_directory
from flask_login import login_required, current_user

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


# API routes should be separate, but using views for now
@views.route("/api/root")
def get_root():
    """Returns the root folder path (Monitor) to the frontend"""
    return jsonify({"root": ROOT_FOLDER})

@views.route("/api/list")
def list_directory():
    """Lists files and folders inside a given directory"""
    requested_path = request.args.get("path", ROOT_FOLDER)

    # Convert to absolute path
    abs_path = os.path.join(ROOT_FOLDER, requested_path.lstrip("/"))

    # Security check: Ensure path is inside ROOT_FOLDER
    if not abs_path.startswith(ROOT_FOLDER):
        return jsonify({"error": "Access Denied"}), 403

    try:
        items = []
        for entry in os.scandir(abs_path):
            items.append({
                "name": entry.name,
                "path": os.path.relpath(entry.path, ROOT_FOLDER),  # Ensure relative path
                "isFolder": entry.is_dir()
            })
        return jsonify({"files": items})
    except PermissionError:
        return jsonify({"error": "Access Denied"}), 403


@views.route("/api/tree")
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
                        "path": os.path.relpath(entry.path, ROOT_FOLDER),  # Relative path
                        "children": build_tree(entry.path)
                    })
        except PermissionError:
            return []  # Return empty if permission is denied
        return tree

    folder_tree = build_tree(ROOT_FOLDER)
    return jsonify(folder_tree)

@views.route("/api/file")
def serve_file():
    """Serves files for viewing"""
    requested_path = request.args.get("path")

    if not requested_path:
        return "Not Found", 404

    # Convert to absolute path
    abs_path = os.path.join(ROOT_FOLDER, requested_path.lstrip("/"))

    # Security check
    if not abs_path.startswith(ROOT_FOLDER) or not os.path.exists(abs_path):
        return "Not Found", 404

    directory = os.path.dirname(abs_path)
    filename = os.path.basename(abs_path)
    return send_from_directory(directory, filename)


# --- New Routes for File Operations --- #

@views.route("/api/create-file", methods=["POST"])
def create_file():
    """Creates a new file in the given directory."""
    data = request.get_json()
    path = data.get("path")
    name = data.get("name")

    if not path or not name:
        return jsonify({"error": "Invalid path or name"}), 400

    # Create file
    file_path = os.path.join(ROOT_FOLDER, path.lstrip("/"), name)
    try:
        with open(file_path, 'w') as f:
            pass  # Create an empty file
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@views.route("/api/create-folder", methods=["POST"])
def create_folder():
    """Creates a new folder in the given directory."""
    data = request.get_json()
    path = data.get("path")
    name = data.get("name")

    if not path or not name:
        return jsonify({"error": "Invalid path or name"}), 400

    # Create folder
    folder_path = os.path.join(ROOT_FOLDER, path.lstrip("/"), name)
    try:
        os.makedirs(folder_path)
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@views.route("/api/edit-item", methods=["POST"])
def edit_item():
    """Renames a file or folder."""
    data = request.get_json()
    path = data.get("path")
    new_name = data.get("newName")

    if not path or not new_name:
        return jsonify({"error": "Invalid path or new name"}), 400

    # Get the absolute path
    abs_path = os.path.join(ROOT_FOLDER, path.lstrip("/"))
    new_path = os.path.join(os.path.dirname(abs_path), new_name)

    try:
        os.rename(abs_path, new_path)
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@views.route("/api/delete-item", methods=["DELETE"])
def delete_item():
    """Deletes a file or folder."""
    data = request.get_json()
    path = data.get("path")

    if not path:
        return jsonify({"error": "Invalid path"}), 400

    # Get the absolute path
    abs_path = os.path.join(ROOT_FOLDER, path.lstrip("/"))

    try:
        if os.path.isdir(abs_path):
            os.rmdir(abs_path)  # Remove directory
        else:
            os.remove(abs_path)  # Remove file
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
