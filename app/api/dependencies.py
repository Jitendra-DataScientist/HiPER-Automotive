from fastapi import Depends
from app.core.auth import get_current_device
from app.services.file_service import FileService

# Dependency to get the FileService instance
def get_file_service(device_id: str = Depends(get_current_device)) -> FileService:
    """
    Dependency to get FileService instance with the authenticated device ID.
    """
    return FileService(device_id)
