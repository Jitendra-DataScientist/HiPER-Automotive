import os
from pathlib import Path
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Settings(BaseSettings):
    PROJECT_NAME: str = "File Transfer API"
    API_PREFIX: str = "/api"
    
    # JWT Settings
    SECRET_KEY: str = os.getenv("SECRET_KEY", "supersecretkey")
    ALGORITHM: str = "HS256"
    # ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 1 day
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 60 * 24))
    
    # Storage settings
    UPLOAD_DIR: Path = Path("uploads")
    TEMP_DIR: Path = Path("uploads/temp")
    
    # Cleanup settings
    CLEANUP_INTERVAL_SECONDS: int = 3600  # Run cleanup every hour
    STALE_UPLOAD_TIMEOUT_SECONDS: int = 86400  # 24 hours
    
    # Create directories if they don't exist
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.UPLOAD_DIR.mkdir(exist_ok=True)
        self.TEMP_DIR.mkdir(exist_ok=True)

# Global settings instance
settings = Settings()
