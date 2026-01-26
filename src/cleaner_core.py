import os
import shutil

def get_external_volumes():
    """
    Returns a list of mounted volumes in /Volumes that are likely external.
    Excludes the startup disk.
    """
    volumes_dir = "/Volumes"
    if not os.path.exists(volumes_dir):
        return []

    external_volumes = []

    # Get the device for the root directory to identify the startup disk
    root_device = os.stat("/").st_dev

    for item in os.listdir(volumes_dir):
        path = os.path.join(volumes_dir, item)
        if os.path.isdir(path):
            try:
                # Check if it is a mount point
                if os.path.ismount(path):
                    # Check if it is the startup disk
                    if os.stat(path).st_dev == root_device:
                        continue

                    # Also specific check for "Macintosh HD" common name if it somehow matches
                    # But the st_dev check is the most reliable way to check if it's the same filesystem as root

                    external_volumes.append(path)
            except OSError:
                continue

    return external_volumes

def scan_for_junk(path):
    """
    Generator that yields paths of .DS_Store and ._ files found in the given path.
    """
    for root, dirs, files in os.walk(path):
        for name in files:
            if name == '.DS_Store' or name.startswith('._'):
                yield os.path.join(root, name)

def clean_files(file_list, dry_run=True, callback=None):
    """
    Removes the files in the list.

    Args:
        file_list: List of file paths to remove.
        dry_run: If True, only simulates removal.
        callback: Optional function to call with (file_path, status_message).

    Returns:
        tuple: (count_success, count_failed)
    """
    success_count = 0
    fail_count = 0

    for file_path in file_list:
        try:
            if not dry_run:
                os.remove(file_path)
                msg = "Deleted"
            else:
                msg = "Would delete"

            success_count += 1
            if callback:
                callback(file_path, msg)

        except Exception as e:
            fail_count += 1
            if callback:
                callback(file_path, f"Error: {str(e)}")

    return success_count, fail_count
