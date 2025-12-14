"""
Fallback PDF handler using PyPDF2 when unstructured is not available.
"""
import logging
from typing import Dict, Any, List
from pathlib import Path

try:
    import PyPDF2
    PYPDF2_AVAILABLE = True
except ImportError:
    PYPDF2_AVAILABLE = False

from .base_handler import BaseFileHandler

logger = logging.getLogger(__name__)


class PDFFallbackHandler(BaseFileHandler):
    """
    Fallback PDF handler using PyPDF2.
    Used when unstructured library is not available.
    """
    
    SUPPORTED_TYPES = ['pdf']
    
    def __init__(self):
        """Initialize the PDF fallback handler."""
        if not PYPDF2_AVAILABLE:
            raise ImportError(
                "PyPDF2 library not available. "
                "Install with: pip install PyPDF2"
            )
    
    def can_handle(self, file_path: str, file_type: str) -> bool:
        """Check if file type is supported."""
        return file_type.lower() == 'pdf' and PYPDF2_AVAILABLE
    
    def get_supported_types(self) -> List[str]:
        """Get list of supported file types."""
        return self.SUPPORTED_TYPES if PYPDF2_AVAILABLE else []
    
    def process(self, file_path: str) -> Dict[str, Any]:
        """
        Process PDF file using PyPDF2.
        
        Args:
            file_path: Path to file
            
        Returns:
            Dictionary with extracted text and metadata
        """
        if not self.validate_file(file_path):
            raise ValueError(f"Invalid file: {file_path}")
        
        try:
            logger.info(f"Processing PDF with PyPDF2: {file_path}")
            
            text_content = []
            metadata = {
                "page_count": 0,
                "has_text": False
            }
            
            with open(file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                metadata["page_count"] = len(pdf_reader.pages)
                
                for page_num, page in enumerate(pdf_reader.pages, 1):
                    try:
                        page_text = page.extract_text()
                        if page_text.strip():
                            text_content.append(f"--- Page {page_num} ---\n{page_text}")
                            metadata["has_text"] = True
                    except Exception as e:
                        logger.warning(f"Error extracting text from page {page_num}: {e}")
                        continue
                
                # Extract document metadata if available
                if pdf_reader.metadata:
                    doc_metadata = pdf_reader.metadata
                    if hasattr(doc_metadata, 'title') and doc_metadata.title:
                        metadata["title"] = doc_metadata.title
                    if hasattr(doc_metadata, 'author') and doc_metadata.author:
                        metadata["author"] = doc_metadata.author
            
            full_text = "\n\n".join(text_content)
            
            if not full_text.strip():
                logger.warning(f"No text extracted from PDF: {file_path}")
                full_text = "[PDF file - text extraction may be limited. For better results, install unstructured[all-docs]]"
            
            # Create simple chunks
            chunks = self._create_simple_chunks(full_text)
            
            return {
                "text": full_text,
                "metadata": metadata,
                "chunks": chunks
            }
            
        except Exception as e:
            logger.error(f"Error processing PDF {file_path}: {str(e)}")
            raise RuntimeError(f"Failed to process PDF: {str(e)}")
    
    def _create_simple_chunks(self, text: str, chunk_size: int = 1000, overlap: int = 200) -> List[Dict[str, Any]]:
        """
        Create simple text chunks.
        
        Args:
            text: Text to chunk
            chunk_size: Size of each chunk
            overlap: Overlap between chunks
            
        Returns:
            List of chunks with text and metadata
        """
        chunks = []
        start = 0
        text_length = len(text)
        chunk_index = 0
        
        while start < text_length:
            end = start + chunk_size
            chunk_text = text[start:end]
            
            # Try to break at sentence boundary
            if end < text_length:
                last_period = chunk_text.rfind('. ')
                last_newline = chunk_text.rfind('\n\n')
                break_point = max(last_period, last_newline)
                
                if break_point > chunk_size * 0.5:
                    chunk_text = chunk_text[:break_point + 1]
                    end = start + break_point + 1
            
            chunks.append({
                "text": chunk_text.strip(),
                "metadata": {
                    "chunk_index": chunk_index,
                    "start_char": start,
                    "end_char": end,
                }
            })
            
            chunk_index += 1
            start = end - overlap
        
        return chunks

