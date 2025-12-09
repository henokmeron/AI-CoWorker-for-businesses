"""
Base file handler interface for extensible document processing.
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, List
from pathlib import Path


class BaseFileHandler(ABC):
    """
    Abstract base class for file handlers.
    
    Custom handlers should inherit from this class and implement
    the required methods to support new file types.
    """
    
    @abstractmethod
    def can_handle(self, file_path: str, file_type: str) -> bool:
        """
        Check if this handler can process the given file.
        
        Args:
            file_path: Path to the file
            file_type: File extension/type
            
        Returns:
            True if this handler can process the file, False otherwise
        """
        pass
    
    @abstractmethod
    def process(self, file_path: str) -> Dict[str, Any]:
        """
        Process the file and extract content.
        
        Args:
            file_path: Path to the file to process
            
        Returns:
            Dictionary containing:
                - text: Extracted text content
                - metadata: Additional metadata (pages, tables, etc.)
                - chunks: Optional pre-chunked content
        """
        pass
    
    @abstractmethod
    def get_supported_types(self) -> List[str]:
        """
        Get list of file types this handler supports.
        
        Returns:
            List of file extensions (without dot)
        """
        pass
    
    def validate_file(self, file_path: str) -> bool:
        """
        Validate that the file exists and is readable.
        
        Args:
            file_path: Path to file
            
        Returns:
            True if file is valid, False otherwise
        """
        path = Path(file_path)
        return path.exists() and path.is_file() and path.stat().st_size > 0
    
    def get_file_info(self, file_path: str) -> Dict[str, Any]:
        """
        Get basic file information.
        
        Args:
            file_path: Path to file
            
        Returns:
            Dictionary with file metadata
        """
        path = Path(file_path)
        return {
            "filename": path.name,
            "extension": path.suffix.lower().lstrip('.'),
            "size": path.stat().st_size,
            "modified": path.stat().st_mtime,
        }


