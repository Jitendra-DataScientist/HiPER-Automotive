import io
from typing import Optional, List
from fastapi import APIRouter, Depends, UploadFile, File, Header, HTTPException, Request, status
from fastapi.responses import StreamingResponse, Response
from app.api.schemas import UploadResponse, FileStatus, FileListResponse
from app.api.dependencies import get_file_service
from app.services.file_service import FileService
from app.core.auth import get_current_device

router = APIRouter(tags=["files"])

@router.post("/files/upload", response_model=UploadResponse)
async def upload_file_chunk(
    filename: str,
    file: UploadFile = File(...),
    content_range: Optional[str] = Header(None),
    file_service: FileService = Depends(get_file_service)
):
    """
    Upload a chunk of a file with a custom binary header.
    
    The binary header contains:
    - start_byte (8 bytes, big-endian)
    - end_byte (8 bytes, big-endian)
    - checksum (1 byte, sum of bytes modulo 256)
    """
    # Read the chunk data with the header
    chunk_data = await file.read()
    
    if len(chunk_data) < 17:  # Minimum size: 8 (start) + 8 (end) + 1 (checksum)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Chunk data too small to contain valid header"
        )
    
    # Parse the binary header
    header_data = chunk_data[:17]
    chunk_data = chunk_data[17:]
    
    # Extract values from header
    start_byte = int.from_bytes(header_data[:8], byteorder='big')
    end_byte = int.from_bytes(header_data[8:16], byteorder='big')
    provided_checksum = header_data[16]
    
    # Compute checksum for validation
    actual_checksum = sum(chunk_data) % 256
    
    if provided_checksum != actual_checksum:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Checksum validation failed"
        )
    
    # Process the chunk
    result = await file_service.save_chunk(
        filename=filename,
        chunk_data=chunk_data,
        start_byte=start_byte,
        end_byte=end_byte
    )
    
    return result

@router.get("/files/download/{filename}")
async def download_file(
    filename: str,
    range: Optional[str] = Header(None),
    file_service: FileService = Depends(get_file_service)
):
    """
    Download a complete file or a specific range.
    Supports partial content requests using the Range header.
    """
    # Check if file exists
    file_status = await file_service.get_file_status(filename)
    if file_status["status"] == "pending" or file_status["status"] == "partial":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File is not complete and cannot be downloaded"
        )
    
    # Get file size
    file_size = file_status["bytes_received"]
    
    # Handle range request
    start_byte = 0
    end_byte = file_size - 1
    
    if range:
        try:
            range_str = range.replace("bytes=", "")
            if "-" in range_str:
                range_parts = range_str.split("-")
                if range_parts[0]:
                    start_byte = int(range_parts[0])
                if range_parts[1]:
                    end_byte = min(int(range_parts[1]), file_size - 1)
            
            # Validate range
            if start_byte >= file_size or start_byte > end_byte:
                raise HTTPException(
                    status_code=status.HTTP_416_REQUESTED_RANGE_NOT_SATISFIABLE,
                    detail=f"Range not satisfiable for file of size {file_size}"
                )
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid range header format"
            )
    
    # Calculate content length
    content_length = end_byte - start_byte + 1
    
    # Create async generator to stream the file
    async def file_stream():
        async for chunk in file_service.read_file_range(filename, start_byte, end_byte):
            yield chunk
    
    # Set appropriate headers
    headers = {
        "Content-Disposition": f"attachment; filename={filename}",
        "Accept-Ranges": "bytes",
        "Content-Length": str(content_length),
    }
    
    # If this is a partial response
    if range:
        headers["Content-Range"] = f"bytes {start_byte}-{end_byte}/{file_size}"
        return StreamingResponse(
            file_stream(),
            status_code=status.HTTP_206_PARTIAL_CONTENT,
            headers=headers,
            media_type="application/octet-stream"
        )
    
    # Full file download
    return StreamingResponse(
        file_stream(),
        headers=headers,
        media_type="application/octet-stream"
    )

@router.get("/files/status/{filename}", response_model=FileStatus)
async def get_file_status(
    filename: str,
    file_service: FileService = Depends(get_file_service)
):
    """
    Get the status of a file upload.
    """
    status = await file_service.get_file_status(filename)
    return FileStatus(
        filename=filename,
        status=status["status"],
        bytes_received=status["bytes_received"],
        total_bytes=status.get("total_bytes"),
        next_expected_byte=status["next_expected_byte"]
    )

@router.get("/files", response_model=FileListResponse)
async def list_files(
    file_service: FileService = Depends(get_file_service)
):
    """
    List all files for the current device.
    """
    files = await file_service.list_files()
    return FileListResponse(files=files)

@router.delete("/files/{filename}")
async def delete_file(
    filename: str,
    file_service: FileService = Depends(get_file_service)
):
    """
    Delete a file or cancel an ongoing upload.
    """
    success = await file_service.delete_file(filename)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"File {filename} not found"
        )
    return {"detail": f"File {filename} deleted successfully"}
