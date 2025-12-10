"""
Patch ChromaDB to avoid onnxruntime dependency issues.
This must be imported BEFORE any chromadb imports.
"""
import sys
import types

def patch_chromadb():
    """Patch ChromaDB's default embedding function to avoid onnxruntime."""
    # Create a mock embedding function class
    class MockEmbeddingFunction:
        def __init__(self, *args, **kwargs):
            pass
        
        def __call__(self, *args, **kwargs):
            raise RuntimeError(
                "Default embedding function is disabled. "
                "Please use OpenAI embeddings by specifying embedding_function parameter."
            )
    
    # Patch the embedding_functions module before chromadb imports it
    if 'chromadb.utils.embedding_functions' not in sys.modules:
        fake_module = types.ModuleType('chromadb.utils.embedding_functions')
        fake_module.DefaultEmbeddingFunction = lambda: MockEmbeddingFunction()
        fake_module.ONNXMiniLM_L6_V2 = lambda: MockEmbeddingFunction()
        sys.modules['chromadb.utils.embedding_functions'] = fake_module

# Apply patch immediately when this module is imported
patch_chromadb()

