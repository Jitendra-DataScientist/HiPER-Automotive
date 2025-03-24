import pytest
import io
from app.utils.file_utils import create_chunk_header, calculate_checksum
from fastapi import status

def test_upload_chunk(authenticated_client, test_device_id):
    """Test uploading a file chunk."""
    # Create test data
    chunk_data = b"Test file content for chunk upload"
    start_byte = 0
    end_byte = len(chunk_data) - 1
    checksum = calculate_checksum(chunk_data)
    
    # Create header and full data
    header = create_chunk_header(start_byte, end_byte, checksum)
    full_data = header + chunk_data
    
    # Create test file
    test_file = io.BytesIO(full_data)
    
    # Upload chunk
    response = authenticated_client.post(
        "/api/files/upload",
        params={"filename": "test_file.txt"},
        files={"file": ("test_file.txt", test_file)}
    )
    
    # Check response
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["filename"] == "test_file.txt"
    assert data["status"] == "complete"
    assert data["bytes_received"] == len(chunk_data)

def test_upload_invalid_checksum(authenticated_client):
    """Test uploading a chunk with invalid checksum."""
    # Create test data with incorrect checksum
    chunk_data = b"Test file content for invalid checksum test"
    start_byte = 0
    end_byte = len(chunk_data) - 1
    invalid_checksum = 255  # Deliberately wrong
    
    # Create header and full data
    header = create_chunk_header(start_byte, end_byte, invalid_checksum)
    full_data = header + chunk_data
    
    # Create test file
    test_file = io.BytesIO(full_data)
    
    # Upload chunk
    response = authenticated_client.post(
        "/api/files/upload",
        params={"filename": "invalid_checksum.txt"},
        files={"file": ("invalid_checksum.txt", test_file)}
    )
    
    # Check response
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "Checksum validation failed" in response.json()["detail"]

def test_file_status(authenticated_client):
    """Test getting file status."""
    # First upload a file
    chunk_data = b"Test file content for status check"
    start_byte = 0
    end_byte = len(chunk_data) - 1
    checksum = calculate_checksum(chunk_data)
    
    header = create_chunk_header(start_byte, end_byte, checksum)
    full_data = header + chunk_data
    
    test_file = io.BytesIO(full_data)
    
    authenticated_client.post(
        "/api/files/upload",
        params={"filename": "status_test.txt"},
        files={"file": ("status_test.txt", test_file)}
    )
    
    # Get status
    response = authenticated_client.get("/api/files/status/status_test.txt")
    
    # Check response
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["filename"] == "status_test.txt"
    assert data["status"] == "complete"
    assert data["bytes_received"] == len(chunk_data)

def test_download_file(authenticated_client):
    """Test downloading a complete file."""
    # First upload a file
    original_content = b"Test file content for download test"
    start_byte = 0
    end_byte = len(original_content) - 1
    checksum = calculate_checksum(original_content)
    
    header = create_chunk_header(start_byte, end_byte, checksum)
    full_data = header + original_content
    
    test_file = io.BytesIO(full_data)
    
    authenticated_client.post(
        "/api/files/upload",
        params={"filename": "download_test.txt"},
        files={"file": ("download_test.txt", test_file)}
    )
    
    # Download the file
    response = authenticated_client.get("/api/files/download/download_test.txt")
    
    # Check response
    assert response.status_code == status.HTTP_200_OK
    assert response.content == original_content

def test_partial_download(authenticated_client):
    """Test downloading a partial file using Range header."""
    # First upload a file
    original_content = b"ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    start_byte = 0
    end_byte = len(original_content) - 1
    checksum = calculate_checksum(original_content)
    
    header = create_chunk_header(start_byte, end_byte, checksum)
    full_data = header + original_content
    
    test_file = io.BytesIO(full_data)
    
    authenticated_client.post(
        "/api/files/upload",
        params={"filename": "partial_test.txt"},
        files={"file": ("partial_test.txt", test_file)}
    )
    
    # Download partial file (bytes 5-15)
    headers = {"Range": "bytes=5-15"}
    response = authenticated_client.get("/api/files/download/partial_test.txt", headers=headers)
    
    # Check response
    assert response.status_code == status.HTTP_206_PARTIAL_CONTENT
    assert response.content == original_content[5:16]  # End is inclusive
    assert response.headers["Content-Range"] == f"bytes 5-15/{len(original_content)}"

def test_list_files(authenticated_client):
    """Test listing files."""
    # Upload multiple files
    for i in range(3):
        content = f"Test content for file {i}".encode()
        start_byte = 0
        end_byte = len(content) - 1
        checksum = calculate_checksum(content)
        
        header = create_chunk_header(start_byte, end_byte, checksum)
        full_data = header + content
        
        test_file = io.BytesIO(full_data)
        
        authenticated_client.post(
            "/api/files/upload",
            params={"filename": f"list_test_{i}.txt"},
            files={"file": (f"list_test_{i}.txt", test_file)}
        )
    
    # List files
    response = authenticated_client.get("/api/files")
    
    # Check response
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "files" in data
    assert len(data["files"]) >= 3
    
    filenames = [file["filename"] for file in data["files"]]
    for i in range(3):
        assert f"list_test_{i}.txt" in filenames

def test_delete_file(authenticated_client):
    """Test deleting a file."""
    # First upload a file
    content = b"Test file content for delete test"
    start_byte = 0
    end_byte = len(content) - 1
    checksum = calculate_checksum(content)
    
    header = create_chunk_header(start_byte, end_byte, checksum)
    full_data = header + content
    
    test_file = io.BytesIO(full_data)
    
    authenticated_client.post(
        "/api/files/upload",
        params={"filename": "delete_test.txt"},
        files={"file": ("delete_test.txt", test_file)}
    )
    
    # Delete the file
    response = authenticated_client.delete("/api/files/delete_test.txt")
    
    # Check response
    assert response.status_code == status.HTTP_200_OK
    
    # Verify file is deleted
    status_response = authenticated_client.get("/api/files/status/delete_test.txt")
    assert status_response.json()["status"] == "pending"
