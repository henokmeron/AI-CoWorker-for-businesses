"""
File handler system for processing various document types.
"""
from .base_handler import BaseFileHandler

# Try to import handlers (may fail if dependencies not installed)
try:
    from .unstructured_handler import UnstructuredFileHandler
except ImportError:
    UnstructuredFileHandler = None

try:
    from .pdf_fallback_handler import PDFFallbackHandler
except ImportError:
    PDFFallbackHandler = None

__all__ = ["BaseFileHandler", "UnstructuredFileHandler", "PDFFallbackHandler"]


