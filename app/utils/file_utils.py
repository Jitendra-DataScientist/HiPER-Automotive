import os
from fastapi import HTTPException, status
from pathlib import Path
from typing import BinaryIO, Tuple

def validate_file_chunk_header(header_data: bytes) -> Tuple[int, int, int]:
    """
    Validate and extract values from a file chunk header.
    
    The header format is:
    - start_byte (8 bytes, big-endian)
    - end_byte (8 bytes, big-endian)
    - checksum (1 byte, sum of bytes modulo 256)
    
    Returns:
        Tuple containing (start_byte, end_byte, checksum)
    """
    if len(header_data) < 17:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid header size"
        )
    
    start_byte = int.from_bytes(header_data[:8], byteorder='big')
    end_byte = int.from_bytes(header_data[8:16], byteorder='big')
    checksum = header_data[16]
    
    if end_byte < start_byte:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid byte range (end_byte < start_byte)"
        )
    
    return start_byte, end_byte, checksum

def calculate_checksum(data: bytes) -> int:
    """
    Calculate checksum as the sum of bytes modulo 256.
    """
    return sum(data) % 256

def create_chunk_header(start_byte: int, end_byte: int, checksum: int) -> bytes:
    """
    Create a binary header for a file chunk.
    """
    header = bytearray(17)
    header[0:8] = start_byte.to_bytes(8, byteorder='big')
    header[8:16] = end_byte.to_bytes(8, byteorder='big')
    header[16] = checksum % 256
    
    return bytes(header)

def ensure_directory_exists(directory_path: Path) -> None:
    """
    Ensure that a directory exists, creating it if necessary.
    """
    directory_path.mkdir(parents=True, exist_ok=True)
