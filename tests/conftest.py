import os
import pytest
import shutil
from pathlib import Path
from fastapi.testclient import TestClient
from main import app
from app.core.config import settings
from app.core.security import create_access_token

@pytest.fixture
def test_device_id():
    return "test_device"

@pytest.fixture
def test_token(test_device_id):
    """Create a test JWT token."""
    return create_access_token(data={"sub": test_device_id})

@pytest.fixture
def test_client():
    """Create a test client for the FastAPI app."""
    return TestClient(app)

@pytest.fixture
def authenticated_client(test_client, test_token):
    """Create an authenticated test client."""
    test_client.headers = {
        "Authorization": f"Bearer {test_token}"
    }
    return test_client

@pytest.fixture(autouse=True)
def clean_test_dirs():
    """Clean up test directories before and after each test."""
    # Setup: create test directories
    test_upload_dir = Path("uploads/test_device")
    test_temp_dir = Path("uploads/temp/test_device")
    test_upload_dir.mkdir(parents=True, exist_ok=True)
    test_temp_dir.mkdir(parents=True, exist_ok=True)
    
    yield
    
    # Teardown: clean test directories
    shutil.rmtree(test_upload_dir, ignore_errors=True)
    shutil.rmtree(test_temp_dir, ignore_errors=True)
