"""
File handler system for processing various document types.
"""
from .base_handler import BaseFileHandler
from .unstructured_handler import UnstructuredFileHandler

__all__ = ["BaseFileHandler", "UnstructuredFileHandler"]

