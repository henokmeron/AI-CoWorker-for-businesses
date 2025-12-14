"""
Universal document processor that orchestrates file handlers.
"""
import logging
import uuid
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime

from .file_handlers import BaseFileHandler
# Import UnstructuredFileHandler separately to handle import errors gracefully
try:
    from .file_handlers import UnstructuredFileHandler
    UNSTRUCTURED_HANDLER_AVAILABLE = True
except ImportError:
    UnstructuredFileHandler = None
    UNSTRUCTURED_HANDLER_AVAILABLE = False

# Import fallback handlers
try:
    from .file_handlers.pdf_fallback_handler import PDFFallbackHandler
    PDF_FALLBACK_AVAILABLE = True
except ImportError:
    PDFFallbackHandler = None
    PDF_FALLBACK_AVAILABLE = False
from ..core.config import settings
from ..utils.file_utils import get_file_extension, ensure_directory

logger = logging.getLogger(__name__)


class DocumentProcessor:
    """
    Main document processing orchestrator.
    
    Manages file handlers and processes documents of various types.
    Uses a plugin system to support extensibility.
    """
    
    def __init__(self):
        """Initialize document processor with file handlers."""
        self.handlers: List[BaseFileHandler] = []
        self._register_default_handlers()
    
    def _register_default_handlers(self):
        """Register default file handlers."""
        logger.info("🔧 Starting handler registration...")
        
        # Direct import attempt with detailed error reporting
        try:
            # Try importing unstructured directly
            logger.info("📦 Testing unstructured library import...")
            from unstructured.partition.auto import partition
            logger.info("✅ unstructured.partition.auto imported successfully")
            
            # Try importing the handler class
            logger.info("📦 Importing UnstructuredFileHandler class...")
            from .file_handlers.unstructured_handler import UnstructuredFileHandler
            logger.info("✅ UnstructuredFileHandler class imported successfully")
            
            # Try creating instance
            logger.info("🔨 Creating UnstructuredFileHandler instance...")
            unstructured_handler = UnstructuredFileHandler(
                enable_ocr=settings.OCR_ENABLED
            )
            logger.info("✅ UnstructuredFileHandler instance created")
            
            # Add to handlers
            self.handlers.append(unstructured_handler)
            supported_types = unstructured_handler.get_supported_types()
            supported_count = len(supported_types)
            logger.info(f"✅✅✅ SUCCESS! Registered UnstructuredFileHandler with {supported_count} file types")
            logger.info(f"📋 Supported types: {', '.join(supported_types[:20])}{'...' if len(supported_types) > 20 else ''}")
            
        except ImportError as e:
            error_msg = str(e)
            logger.error(f"❌ ImportError during handler registration: {e}", exc_info=True)
            logger.error(f"Import error details: {type(e).__name__}: {error_msg}")
            
            # Provide specific guidance based on error type
            if "libGL.so.1" in error_msg or "libGL" in error_msg:
                logger.error("⚠️ Missing OpenGL system library (libGL.so.1)")
                logger.error("This is required for OpenCV which unstructured uses for image processing")
                logger.error("Solution: Install libgl1-mesa-glx in Dockerfile:")
                logger.error("  RUN apt-get update && apt-get install -y libgl1-mesa-glx libglib2.0-0")
            elif "cv2" in error_msg or "opencv" in error_msg.lower():
                logger.error("⚠️ OpenCV import failed - missing system dependencies")
                logger.error("Install: libgl1-mesa-glx libglib2.0-0 libsm6 libxext6 libxrender-dev")
            elif "unstructured" in error_msg.lower():
                logger.error("The unstructured library may be installed but missing dependencies")
                logger.error("Try: pip install unstructured[all-docs] --upgrade")
            else:
                logger.error("This usually means unstructured library dependencies are missing")
                logger.error("Install with: pip install unstructured[all-docs]")
        except Exception as e:
            logger.error(f"❌ Exception creating UnstructuredFileHandler: {type(e).__name__}: {e}", exc_info=True)
            logger.error("Full traceback above should show the exact issue")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
        
        # Register fallback handlers if unstructured is not available
        if len(self.handlers) == 0 or not UNSTRUCTURED_HANDLER_AVAILABLE:
            logger.warning("⚠️ Unstructured handler not available, registering fallback handlers...")
            try:
                if PDF_FALLBACK_AVAILABLE and PDFFallbackHandler:
                    pdf_handler = PDFFallbackHandler()
                    self.handlers.append(pdf_handler)
                    logger.info(f"✅ Registered PDF fallback handler (PyPDF2)")
            except Exception as e:
                logger.warning(f"Could not register PDF fallback handler: {e}")
        
        # Log final handler count
        logger.info(f"📊 Total handlers registered: {len(self.handlers)}")
        if len(self.handlers) == 0:
            logger.error("⚠️⚠️⚠️ CRITICAL: NO FILE HANDLERS REGISTERED! File uploads will fail!")
            logger.error("Check the error messages above to diagnose the issue")
            logger.error("Install dependencies: pip install unstructured[all-docs] OR pip install PyPDF2")
        else:
            logger.info(f"✅ Handler registration complete! {len(self.handlers)} handler(s) ready")
        
        # TODO: Add more specialized handlers here if needed
        # self.handlers.append(CustomPDFHandler())
        # self.handlers.append(CustomExcelHandler())
    
    def register_handler(self, handler: BaseFileHandler):
        """
        Register a custom file handler.
        
        Args:
            handler: Custom file handler instance
        """
        self.handlers.append(handler)
        logger.info(f"Registered custom handler: {handler.__class__.__name__}")
    
    def get_handler(self, file_path: str) -> Optional[BaseFileHandler]:
        """
        Find appropriate handler for a file.
        
        Args:
            file_path: Path to file
            
        Returns:
            Appropriate file handler or None
        """
        file_type = get_file_extension(Path(file_path).name)
        
        for handler in self.handlers:
            if handler.can_handle(file_path, file_type):
                return handler
        
        return None
    
    def get_supported_types(self) -> List[str]:
        """
        Get all supported file types from all handlers.
        
        Returns:
            List of supported file extensions
        """
        supported = set()
        for handler in self.handlers:
            supported.update(handler.get_supported_types())
        return sorted(list(supported))
    
    def process_document(
        self,
        file_path: str,
        business_id: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Process a document and extract content.
        
        Args:
            file_path: Path to file
            business_id: Business ID for this document
            metadata: Optional additional metadata
            
        Returns:
            Processed document with text, chunks, and metadata
            
        Raises:
            ValueError: If file type not supported
            RuntimeError: If processing fails
        """
        file_type = get_file_extension(Path(file_path).name)
        
        # Find appropriate handler
        handler = self.get_handler(file_path)
        if not handler:
            supported = self.get_supported_types()
            # Try fallback handlers for specific file types
            if file_type.lower() == 'pdf':
                logger.warning(f"No PDF handler found, trying fallback...")
                try:
                    if PDF_FALLBACK_AVAILABLE and PDFFallbackHandler:
                        handler = PDFFallbackHandler()
                        if handler.can_handle(file_path, file_type):
                            logger.info(f"Using PDF fallback handler (PyPDF2) for {file_type}")
                        else:
                            handler = None
                except Exception as e:
                    logger.error(f"PDF fallback handler failed: {e}")
                    handler = None
            
            if not handler:
                if not supported:
                    raise ValueError(
                        f"Unsupported file type: {file_type}. "
                        f"No handlers registered. Install dependencies: pip install unstructured[all-docs] OR pip install PyPDF2"
                    )
                else:
                    raise ValueError(
                        f"Unsupported file type: {file_type}. "
                        f"Supported types: {', '.join(supported)}"
                    )
        
        logger.info(f"Processing {file_path} with {handler.__class__.__name__}")
        
        try:
            # Process the file
            result = handler.process(file_path)
            
            # Add document-level metadata
            doc_id = str(uuid.uuid4())
            result["document_id"] = doc_id
            result["business_id"] = business_id
            result["file_path"] = file_path
            result["processed_at"] = datetime.utcnow().isoformat()
            
            # Merge additional metadata if provided
            if metadata:
                result["metadata"].update(metadata)
            
            # Create semantic chunks if not already done
            if not result.get("chunks"):
                result["chunks"] = self._create_chunks(result["text"])
            
            logger.info(
                f"Successfully processed document {doc_id}: "
                f"{len(result['chunks'])} chunks created"
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Error processing document {file_path}: {str(e)}")
            raise RuntimeError(f"Document processing failed: {str(e)}")
    
    def _create_chunks(
        self,
        text: str,
        chunk_size: Optional[int] = None,
        chunk_overlap: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Create text chunks from extracted text.
        
        Args:
            text: Text to chunk
            chunk_size: Size of each chunk (default from settings)
            chunk_overlap: Overlap between chunks (default from settings)
            
        Returns:
            List of chunks with text and metadata
        """
        chunk_size = chunk_size or settings.CHUNK_SIZE
        chunk_overlap = chunk_overlap or settings.CHUNK_OVERLAP
        
        # Simple chunking by character count with overlap
        chunks = []
        start = 0
        text_length = len(text)
        chunk_index = 0
        
        while start < text_length:
            end = start + chunk_size
            chunk_text = text[start:end]
            
            # Try to break at sentence boundary
            if end < text_length:
                # Look for sentence ending
                last_period = chunk_text.rfind('. ')
                last_newline = chunk_text.rfind('\n\n')
                break_point = max(last_period, last_newline)
                
                if break_point > chunk_size * 0.5:  # Don't break too early
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
            start = end - chunk_overlap
        
        return chunks
    
    def save_document(
        self,
        source_path: str,
        business_id: str,
        filename: str
    ) -> str:
        """
        Save uploaded document to business directory.
        
        Args:
            source_path: Temporary upload path
            business_id: Business ID
            filename: Original filename
            
        Returns:
            Path to saved document
        """
        # Create business directory
        business_dir = Path(settings.UPLOAD_DIR) / business_id
        ensure_directory(str(business_dir))
        
        # Generate unique filename to avoid conflicts
        file_ext = get_file_extension(filename)
        unique_name = f"{uuid.uuid4()}.{file_ext}"
        dest_path = business_dir / unique_name
        
        # Copy file
        import shutil
        shutil.copy2(source_path, dest_path)
        
        logger.info(f"Saved document to {dest_path}")
        return str(dest_path)


# Global processor instance
_processor = None


def get_document_processor() -> DocumentProcessor:
    """
    Get global document processor instance (singleton).
    
    Returns:
        DocumentProcessor instance
    """
    global _processor
    if _processor is None:
        _processor = DocumentProcessor()
    return _processor


