import asyncio
import logging
from fastapi import FastAPI
from pathlib import Path
import json
import aiofiles
import os
from datetime import datetime
from app.core.config import settings

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("cleanup_service")

async def cleanup_stale_uploads():
    """
    Periodically check for and process stale uploads.
    Stale uploads are partial uploads that haven't been updated for a defined period.
    """
    while True:
        try:
            logger.info("Running cleanup task for stale uploads")
            current_time = asyncio.get_event_loop().time()
            stale_threshold = current_time - settings.STALE_UPLOAD_TIMEOUT_SECONDS
            
            # Scan device directories
            for device_dir in settings.UPLOAD_DIR.iterdir():
                if not device_dir.is_dir() or device_dir == settings.TEMP_DIR:
                    continue
                
                device_id = device_dir.name
                
                # Check metadata files for stale uploads
                for meta_path in device_dir.glob("*.meta"):
                    try:
                        # Read metadata
                        async with aiofiles.open(meta_path, "r") as f:
                            metadata = json.loads(await f.read())
                        
                        # Check if stale
                        if metadata.get("last_update", 0) < stale_threshold:
                            filename = meta_path.name[:-5]  # Remove .meta extension
                            logger.info(f"Found stale upload: {filename} for device {device_id}")
                            
                            # Process the stale upload (save what we have)
                            await process_stale_upload(device_id, filename, metadata)
                    except Exception as e:
                        logger.error(f"Error processing metadata file {meta_path}: {str(e)}")
            
            # Clean up temp directory
            temp_dir = settings.TEMP_DIR
            if temp_dir.exists():
                for temp_file in temp_dir.glob("**/*"):
                    if temp_file.is_file() and temp_file.stat().st_mtime < stale_threshold:
                        logger.info(f"Removing stale temp file: {temp_file}")
                        temp_file.unlink()
        
        except Exception as e:
            logger.error(f"Error in cleanup task: {str(e)}")
        
        # Wait for next run
        await asyncio.sleep(settings.CLEANUP_INTERVAL_SECONDS)

async def process_stale_upload(device_id: str, filename: str, metadata: dict):
    """
    Process a stale upload by saving the partial file and cleaning up chunks.
    """
    device_dir = settings.UPLOAD_DIR / device_id
    temp_dir = settings.TEMP_DIR / device_id
    
    # Create a partial file from available chunks
    partial_filename = f"{filename}.partial"
    partial_path = device_dir / partial_filename
    
    try:
        # Get chunks and sort them
        chunks = []
        for chunk_key, chunk_info in metadata["chunks"].items():
            chunks.append((chunk_info["start_byte"], chunk_info["end_byte"]))
        chunks.sort()
        
        # Create the partial file
        async with aiofiles.open(partial_path, "wb") as out_file:
            for start_byte, end_byte in chunks:
                chunk_path = temp_dir / f"{filename}.{start_byte}-{end_byte}"
                if chunk_path.exists():
                    await out_file.seek(start_byte)
                    async with aiofiles.open(chunk_path, "rb") as in_file:
                        await out_file.write(await in_file.read())
                    
                    # Remove the chunk file
                    chunk_path.unlink()
        
        # Update metadata to indicate partial status
        metadata["status"] = "partial"
        metadata["processed_date"] = datetime.now().isoformat()
        
        # Save updated metadata
        async with aiofiles.open(device_dir / f"{partial_filename}.meta", "w") as f:
            await f.write(json.dumps(metadata))
        
        # Remove original metadata
        meta_path = device_dir / f"{filename}.meta"
        if meta_path.exists():
            meta_path.unlink()
        
        logger.info(f"Successfully processed stale upload: {filename} -> {partial_filename}")
    
    except Exception as e:
        logger.error(f"Error processing stale upload {filename}: {str(e)}")

def setup_cleanup_tasks(app: FastAPI):
    """
    Set up background tasks for the FastAPI application.
    """
    @app.on_event("startup")
    async def start_cleanup_task():
        asyncio.create_task(cleanup_stale_uploads())
