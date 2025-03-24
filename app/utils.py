import os
from fastapi import HTTPException, Request
from fastapi.responses import StreamingResponse
from typing import Generator

CHUNK_SIZE = 8192  # 8KB

def save_chunk(file_id: str, chunk_number: int, chunk_data: bytes):
    """
    Save an uploaded file chunk to a temporary directory.
    """
    temp_dir = os.path.join("data", "temp_chunks", file_id)
    os.makedirs(temp_dir, exist_ok=True)
    chunk_path = os.path.join(temp_dir, f"chunk_{chunk_number}")
    with open(chunk_path, "wb") as chunk_file:
        chunk_file.write(chunk_data)

def assemble_file(file_id: str):
    """
    Assemble all chunks of a file into the final file.
    """
    temp_dir = os.path.join("data", "temp_chunks", file_id)
    output_dir = os.path.join("data", "uploads")
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, file_id)
    with open(output_path, "wb") as output_file:
        chunk_number = 1
        while True:
            chunk_path = os.path.join(temp_dir, f"chunk_{chunk_number}")
            if not os.path.exists(chunk_path):
                break
            with open(chunk_path, "rb") as chunk_file:
                output_file.write(chunk_file.read())
            os.remove(chunk_path)
            chunk_number += 1
    os.rmdir(temp_dir)

def get_file_path(file_id: str) -> str:
    """
    Get the path to a stored file.
    """
    return os.path.join("data", "uploads", file_id)

def file_iterator(file_path: str, start: int = 0, end: int = None) -> Generator[bytes, None, None]:
    """
    File generator to read a file in chunks.
    """
    with open(file_path, "rb") as f:
        f.seek(start)
        while True:
            bytes_to_read = CHUNK_SIZE if end is None else min(CHUNK_SIZE, end - f.tell() + 1)
            data = f.read(bytes_to_read)
            if not data:
                break
            yield data
            if end is not None and f.tell() > end:
                break

def parse_range_header(range_header: str, file_size: int):
    """
    Parse the Range header to determine the start and end bytes.
    """
    if not range_header or '=' not in range_header:
        return None, None
    range_type, range_value = range_header.split('=', 1)
    if range_type != 'bytes':
        return None, None
    start_str, end_str = range_value.split('-')
    start = int(start_str) if start_str else 0
    end = int(end_str) if end_str else file_size - 1
    return start, end

def range_requests_response(request: Request, file_path: str) -> StreamingResponse:
    """
    Handle range requests for partial file downloads.
    """
    file_size = os.path.getsize(file_path)
    range_header = request.headers.get('Range')
    start, end = parse_range_header(range_header, file_size)
    if start is None or end is None or start >= file_size or end >= file_size:
        raise HTTPException(status_code=416, detail="Invalid range")
    headers = {
        'Content-Range': f'bytes {start}-{end}/{file_size}',
        'Accept-Ranges': 'bytes',
    }
    return StreamingResponse(
        file_iterator(file_path, start, end + 1),
        status_code=206,
        headers=headers,
        media_type='application/octet-stream'
    )
