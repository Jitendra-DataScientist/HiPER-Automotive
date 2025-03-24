import os
import json
import asyncio
import aiofiles
from pathlib import Path
from typing import Dict, List, Optional, AsyncGenerator, Any
from fastapi import HTTPException, status
from app.core.config import settings

class FileService:
    """
    Service to handle file operations including chunked uploads, downloads,
    and status tracking.
    """
    
    def __init__(self, device_id: str):
        self.device_id = device_id
        self.device_dir = settings.UPLOAD_DIR / device_id
        self.temp_dir = settings.TEMP_DIR / device_id
        
        # Create device directories if they don't exist
        self.device_dir.mkdir(exist_ok=True, parents=True)
        self.temp_dir.mkdir(exist_ok=True, parents=True)
        
        # In-memory cache for active uploads
        self._active_uploads = {}  # {filename: {chunks: {}, last_update: timestamp}}
    
    async def save_chunk(self, filename: str, chunk_data: bytes, start_byte: int, end_byte: int) -> Dict[str, Any]:
        """
        Save a chunk of file data and track its position.
        """
        # Get or initialize file metadata
        metadata = await self._get_file_metadata(filename)
        
        # Update the metadata with new chunk information
        chunk_key = f"{start_byte}-{end_byte}"
        metadata["chunks"][chunk_key] = {
            "start_byte": start_byte,
            "end_byte": end_byte,
            "size": len(chunk_data),
            "last_update": asyncio.get_event_loop().time()
        }
        
        # Save the chunk to temporary storage
        chunk_path = self.temp_dir / f"{filename}.{start_byte}-{end_byte}"
        async with aiofiles.open(chunk_path, "wb") as f:
            await f.write(chunk_data)
        
        # Update metadata with total size if this is the last chunk
        if "total_bytes" not in metadata or end_byte + 1 > metadata["total_bytes"]:
            metadata["total_bytes"] = end_byte + 1
        
        # Calculate bytes received and next expected byte
        received_ranges = self._calculate_received_ranges(metadata["chunks"])
        bytes_received = sum(end - start + 1 for start, end in received_ranges)
        next_expected_byte = self._calculate_next_expected_byte(received_ranges, metadata.get("total_bytes", 0))
        
        # Check if the file is complete
        if bytes_received == metadata.get("total_bytes", 0):
            # All chunks received, assemble the file
            await self._assemble_complete_file(filename, metadata)
            status = "complete"
        else:
            # Update the metadata
            await self._save_metadata(filename, metadata)
            status = "partial"
        
        # Return the updated status
        return {
            "filename": filename,
            "status": status,
            "bytes_received": bytes_received,
            "total_bytes": metadata.get("total_bytes"),
            "next_expected_byte": next_expected_byte
        }
    
    async def get_file_status(self, filename: str) -> Dict[str, Any]:
        """
        Get the current status of a file upload.
        """
        # Check if the complete file exists
        complete_file_path = self.device_dir / filename
        if complete_file_path.exists():
            file_size = complete_file_path.stat().st_size
            return {
                "status": "complete",
                "bytes_received": file_size,
                "total_bytes": file_size,
                "next_expected_byte": file_size
            }
        
        # Check if we have metadata for a partial upload
        try:
            metadata = await self._get_file_metadata(filename)
            received_ranges = self._calculate_received_ranges(metadata["chunks"])
            bytes_received = sum(end - start + 1 for start, end in received_ranges)
            next_expected_byte = self._calculate_next_expected_byte(received_ranges, metadata.get("total_bytes", 0))
            
            return {
                "status": "partial",
                "bytes_received": bytes_received,
                "total_bytes": metadata.get("total_bytes"),
                "next_expected_byte": next_expected_byte
            }
        except FileNotFoundError:
            # No metadata found, file is pending
            return {
                "status": "pending",
                "bytes_received": 0,
                "total_bytes": None,
                "next_expected_byte": 0
            }
    
    async def read_file_range(self, filename: str, start_byte: int, end_byte: int) -> AsyncGenerator[bytes, None]:
        """
        Read a range of bytes from a file and yield chunks.
        Used for streaming file downloads.
        """
        file_path = self.device_dir / filename
        if not file_path.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"File {filename} not found"
            )
        
        chunk_size = 1024 * 1024  # 1MB chunks for streaming
        async with aiofiles.open(file_path, "rb") as f:
            await f.seek(start_byte)
            bytes_to_read = end_byte - start_byte + 1
            bytes_read = 0
            
            while bytes_read < bytes_to_read:
                current_chunk_size = min(chunk_size, bytes_to_read - bytes_read)
                chunk = await f.read(current_chunk_size)
                if not chunk:
                    break
                bytes_read += len(chunk)
                yield chunk
    
    async def list_files(self) -> List[Dict[str, Any]]:
        """
        List all files for the current device with their status.
        """
        files = []
        
        # List complete files
        for file_path in self.device_dir.glob("*"):
            if file_path.is_file() and not file_path.name.endswith(".meta"):
                file_size = file_path.stat().st_size
                files.append({
                    "filename": file_path.name,
                    "status": "complete",
                    "bytes_received": file_size,
                    "total_bytes": file_size,
                    "next_expected_byte": file_size
                })
        
        # List partial uploads
        for meta_path in self.device_dir.glob("*.meta"):
            filename = meta_path.name[:-5]  # Remove .meta extension
            
            # Skip if complete file already exists
            if (self.device_dir / filename).exists():
                continue
                
            try:
                metadata = await self._get_file_metadata(filename)
                received_ranges = self._calculate_received_ranges(metadata["chunks"])
                bytes_received = sum(end - start + 1 for start, end in received_ranges)
                next_expected_byte = self._calculate_next_expected_byte(received_ranges, metadata.get("total_bytes", 0))
                
                files.append({
                    "filename": filename,
                    "status": "partial",
                    "bytes_received": bytes_received,
                    "total_bytes": metadata.get("total_bytes"),
                    "next_expected_byte": next_expected_byte
                })
            except Exception:
                # Skip files with corrupted metadata
                continue
        
        return files
    
    async def delete_file(self, filename: str) -> bool:
        """
        Delete a file or cancel an upload.
        """
        # Check for complete file
        complete_file = self.device_dir / filename
        if complete_file.exists():
            complete_file.unlink()
            return True
        
        # Check for metadata
        meta_file = self.device_dir / f"{filename}.meta"
        if meta_file.exists():
            # Get chunks to delete
            try:
                metadata = await self._get_file_metadata(filename)
                # Delete all chunk files
                for chunk_key in metadata["chunks"].keys():
                    chunk_path = self.temp_dir / f"{filename}.{chunk_key}"
                    if chunk_path.exists():
                        chunk_path.unlink()
            except Exception:
                pass
            
            # Delete metadata
            meta_file.unlink()
            return True
        
        return False
    
    async def _get_file_metadata(self, filename: str) -> Dict[str, Any]:
        """
        Get or initialize metadata for a file.
        """
        meta_path = self.device_dir / f"{filename}.meta"
        
        if meta_path.exists():
            async with aiofiles.open(meta_path, "r") as f:
                content = await f.read()
                return json.loads(content)
        
        # Initialize new metadata
        metadata = {
            "filename": filename,
            "device_id": self.device_id,
            "chunks": {},
            "created_at": asyncio.get_event_loop().time(),
            "last_update": asyncio.get_event_loop().time()
        }
        
        await self._save_metadata(filename, metadata)
        return metadata
    
    async def _save_metadata(self, filename: str, metadata: Dict[str, Any]) -> None:
        """
        Save metadata for a file.
        """
        metadata["last_update"] = asyncio.get_event_loop().time()
        meta_path = self.device_dir / f"{filename}.meta"
        
        async with aiofiles.open(meta_path, "w") as f:
            await f.write(json.dumps(metadata))
    
    def _calculate_received_ranges(self, chunks: Dict[str, Dict[str, Any]]) -> List[tuple]:
        """
        Calculate continuous byte ranges that have been received.
        """
        if not chunks:
            return []
        
        # Extract start and end bytes
        ranges = [(chunk["start_byte"], chunk["end_byte"]) for chunk in chunks.values()]
        ranges.sort()
        
        # Merge overlapping ranges
        merged = []
        for current in ranges:
            if not merged or current[0] > merged[-1][1] + 1:
                merged.append(current)
            else:
                merged[-1] = (merged[-1][0], max(merged[-1][1], current[1]))
        
        return merged
    
    def _calculate_next_expected_byte(self, ranges: List[tuple], total_bytes: Optional[int]) -> int:
        """
        Calculate the next byte that should be received.
        """
        if not ranges:
            return 0
        
        # Find the first gap or the end of the file
        last_end = 0
        for start, end in ranges:
            if start > last_end:
                return last_end
            last_end = max(last_end, end + 1)
        
        return last_end
    
    async def _assemble_complete_file(self, filename: str, metadata: Dict[str, Any]) -> None:
        """
        Assemble a complete file from chunks.
        """
        # Get all chunk ranges
        ranges = [(chunk["start_byte"], chunk["end_byte"]) for chunk in metadata["chunks"].values()]
        ranges.sort()
        
        # Create or open the output file
        output_path = self.device_dir / filename
        async with aiofiles.open(output_path, "wb") as out_file:
            # Process each chunk in order
            for start_byte, end_byte in ranges:
                chunk_path = self.temp_dir / f"{filename}.{start_byte}-{end_byte}"
                
                if not chunk_path.exists():
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail=f"Chunk file missing during assembly: {start_byte}-{end_byte}"
                    )
                
                # Seek to the correct position and write the chunk
                await out_file.seek(start_byte)
                async with aiofiles.open(chunk_path, "rb") as in_file:
                    await out_file.write(await in_file.read())
        
        # Clean up chunk files and metadata
        for start_byte, end_byte in ranges:
            chunk_path = self.temp_dir / f"{filename}.{start_byte}-{end_byte}"
            if chunk_path.exists():
                chunk_path.unlink()
        
        # Delete metadata file
        meta_path = self.device_dir / f"{filename}.meta"
        if meta_path.exists():
            meta_path.unlink()
