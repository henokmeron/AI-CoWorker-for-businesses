"""
Universal file handler using Unstructured.io library.
Supports 30+ file types including PDF, DOCX, PPTX, XLSX, images, emails, etc.
"""
import logging
from typing import Dict, Any, List
from pathlib import Path

try:
    from unstructured.partition.auto import partition
    from unstructured.chunking.title import chunk_by_title
    UNSTRUCTURED_AVAILABLE = True
except ImportError:
    UNSTRUCTURED_AVAILABLE = False

from .base_handler import BaseFileHandler

logger = logging.getLogger(__name__)


class UnstructuredFileHandler(BaseFileHandler):
    """
    Universal file handler using Unstructured.io.
    
    Supports a wide range of file types:
    - Documents: PDF, DOCX, PPTX, ODT, RTF
    - Spreadsheets: XLSX, CSV, ODS
    - Text: TXT, Markdown, HTML, XML, JSON
    - Images: PNG, JPG, TIFF (with OCR)
    - Emails: EML, MSG
    - Code: Python, JavaScript, Java, etc.
    """
    
    # Comprehensive list of supported file types
    SUPPORTED_TYPES = [
        # Documents
        'pdf', 'doc', 'docx', 'ppt', 'pptx', 'odt', 'rtf',
        # Spreadsheets
        'xlsx', 'xls', 'csv', 'ods',
        # Text formats
        'txt', 'md', 'markdown', 'html', 'htm', 'xml', 'json',
        # Images (with OCR)
        'png', 'jpg', 'jpeg', 'tiff', 'tif', 'bmp',
        # Emails
        'eml', 'msg',
        # Code files
        'py', 'js', 'java', 'cpp', 'c', 'h', 'cs', 'rb', 'go',
        'php', 'swift', 'kt', 'rs', 'ts', 'tsx', 'jsx',
        # Other
        'epub', 'rst', 'org'
    ]
    
    def __init__(self, enable_ocr: bool = True):
        """
        Initialize the Unstructured handler.
        
        Args:
            enable_ocr: Enable OCR for image-based content
        """
        if not UNSTRUCTURED_AVAILABLE:
            raise ImportError(
                "Unstructured library not available. "
                "Install with: pip install unstructured[all-docs]"
            )
        self.enable_ocr = enable_ocr
    
    def can_handle(self, file_path: str, file_type: str) -> bool:
        """Check if file type is supported."""
        return file_type.lower() in self.SUPPORTED_TYPES
    
    def get_supported_types(self) -> List[str]:
        """Get list of supported file types."""
        return self.SUPPORTED_TYPES
    
    def process(self, file_path: str) -> Dict[str, Any]:
        """
        Process file using Unstructured.io.
        
        Args:
            file_path: Path to file
            
        Returns:
            Dictionary with extracted text and metadata
        """
        if not self.validate_file(file_path):
            raise ValueError(f"Invalid file: {file_path}")
        
        try:
            logger.info(f"Processing file with Unstructured: {file_path}")
            
            # Partition the document into elements
            # Unstructured automatically detects file type and applies appropriate processing
            elements = partition(
                filename=file_path,
                strategy="auto",  # Auto-detect best strategy
                include_page_breaks=True,
                ocr_languages="eng" if self.enable_ocr else None,
            )
            
            # Extract text from elements
            text_content = "\n\n".join([str(element) for element in elements])
            
            # Extract metadata
            metadata = self._extract_metadata(elements, file_path)
            
            # Create chunks (optional, can be done later)
            chunks = self._create_chunks(elements)
            
            return {
                "text": text_content,
                "metadata": metadata,
                "chunks": chunks,
                "elements": [
                    {
                        "text": str(elem),
                        "type": elem.category if hasattr(elem, 'category') else "unknown",
                        "metadata": elem.metadata.to_dict() if hasattr(elem, 'metadata') else {}
                    }
                    for elem in elements
                ]
            }
            
        except Exception as e:
            logger.error(f"Error processing file {file_path}: {str(e)}")
            raise RuntimeError(f"Failed to process file: {str(e)}")
    
    def _extract_metadata(self, elements: List, file_path: str) -> Dict[str, Any]:
        """
        Extract metadata from processed elements.
        
        Args:
            elements: List of document elements
            file_path: Original file path
            
        Returns:
            Metadata dictionary
        """
        file_info = self.get_file_info(file_path)
        
        # Count different element types
        element_types = {}
        pages = set()
        
        for elem in elements:
            elem_type = elem.category if hasattr(elem, 'category') else "unknown"
            element_types[elem_type] = element_types.get(elem_type, 0) + 1
            
            # Extract page numbers if available
            if hasattr(elem, 'metadata') and hasattr(elem.metadata, 'page_number'):
                if elem.metadata.page_number:
                    pages.add(elem.metadata.page_number)
        
        metadata = {
            **file_info,
            "element_count": len(elements),
            "element_types": element_types,
            "page_count": len(pages) if pages else None,
            "has_tables": "Table" in element_types,
            "has_images": "Image" in element_types,
        }
        
        return metadata
    
    def _create_chunks(self, elements: List) -> List[Dict[str, Any]]:
        """
        Create semantic chunks from elements.
        
        Args:
            elements: List of document elements
            
        Returns:
            List of chunks with text and metadata
        """
        try:
            # Use Unstructured's chunking functionality
            chunks = chunk_by_title(
                elements,
                max_characters=1000,
                combine_text_under_n_chars=200,
            )
            
            return [
                {
                    "text": str(chunk),
                    "metadata": chunk.metadata.to_dict() if hasattr(chunk, 'metadata') else {}
                }
                for chunk in chunks
            ]
        except Exception as e:
            logger.warning(f"Chunking failed, using simple text split: {str(e)}")
            # Fallback to simple chunking
            full_text = "\n\n".join([str(elem) for elem in elements])
            return [{"text": full_text, "metadata": {}}]

