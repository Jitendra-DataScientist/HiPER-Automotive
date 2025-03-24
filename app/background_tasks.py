import os
import shutil
from datetime import datetime, timedelta

INCOMPLETE_UPLOAD_THRESHOLD = timedelta(hours=1)

def cleanup_incomplete_uploads():
    """
    Move incomplete uploads to permanent storage and free up resources.
    """
    temp_dir = os.path.join("data", "temp_chunks")
    if not os.path.exists(temp_dir):
        return
    for file_id in os.listdir(temp_dir):
        file_dir = os.path.join(temp_dir, file_id)
        if not os.path.isdir(file_dir):
            continue
        last_modified = datetime.fromtimestamp(os.path.getmtime(file_dir))
        if datetime.utcnow() - last_modified > INCOMPLETE_UPLOAD_THRESHOLD:
            # Assemble and move incomplete upload to permanent storage
            assemble_file(file_id)
            shutil.rmtree(file_dir)
