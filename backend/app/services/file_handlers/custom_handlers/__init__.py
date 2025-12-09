"""
Directory for custom file handlers.

To add a custom handler:
1. Create a new file (e.g., my_handler.py)
2. Inherit from BaseFileHandler
3. Implement required methods: can_handle, process, get_supported_types
4. Register in the document processor

Example:
    from ..base_handler import BaseFileHandler
    
    class MyCustomHandler(BaseFileHandler):
        def can_handle(self, file_path: str, file_type: str) -> bool:
            return file_type == 'custom'
        
        def process(self, file_path: str) -> Dict[str, Any]:
            # Your processing logic
            return {"text": processed_text, "metadata": {}}
        
        def get_supported_types(self) -> List[str]:
            return ['custom']
"""


