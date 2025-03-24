from pydantic import BaseModel, Field
from typing import Optional, List

class UploadResponse(BaseModel):
    filename: str
    status: str
    bytes_received: int
    total_bytes: Optional[int] = None
    next_expected_byte: int

class FileStatus(BaseModel):
    filename: str
    status: str  # "complete", "partial", "pending"
    bytes_received: int
    total_bytes: Optional[int] = None
    next_expected_byte: int

class FileListResponse(BaseModel):
    files: List[FileStatus]
