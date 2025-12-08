"""
File utility functions.
"""
import os
import hashlib
import mimetypes
from pathlib import Path
from typing import Optional


def get_file_hash(file_path: str) -> str:
    """
    Generate SHA256 hash of a file.
    
    Args:
        file_path: Path to file
        
    Returns:
        Hexadecimal hash string
    """
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()


def get_file_extension(filename: str) -> str:
    """
    Get file extension from filename.
    
    Args:
        filename: Name of file
        
    Returns:
        File extension (lowercase, without dot)
    """
    return Path(filename).suffix.lower().lstrip('.')


def get_mime_type(filename: str) -> Optional[str]:
    """
    Get MIME type of file.
    
    Args:
        filename: Name of file
        
    Returns:
        MIME type string or None
    """
    mime_type, _ = mimetypes.guess_type(filename)
    return mime_type


def ensure_directory(directory: str) -> None:
    """
    Create directory if it doesn't exist.
    
    Args:
        directory: Path to directory
    """
    Path(directory).mkdir(parents=True, exist_ok=True)


def get_file_size(file_path: str) -> int:
    """
    Get file size in bytes.
    
    Args:
        file_path: Path to file
        
    Returns:
        File size in bytes
    """
    return os.path.getsize(file_path)


def is_file_allowed(filename: str, max_size_mb: int, file_size: int) -> tuple[bool, str]:
    """
    Check if file is allowed based on size.
    
    Args:
        filename: Name of file
        max_size_mb: Maximum allowed size in MB
        file_size: Actual file size in bytes
        
    Returns:
        Tuple of (is_allowed, error_message)
    """
    max_size_bytes = max_size_mb * 1024 * 1024
    
    if file_size > max_size_bytes:
        return False, f"File size exceeds maximum allowed size of {max_size_mb}MB"
    
    return True, ""

