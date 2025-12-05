"""
LangChain compatibility shim for missing attributes.

This module patches the langchain module to add missing attributes that some
LangChain components may try to access in newer versions.
"""

try:
    import langchain
    # Add missing attributes if they don't exist
    if not hasattr(langchain, 'verbose'):
        langchain.verbose = False
    if not hasattr(langchain, 'debug'):
        langchain.debug = False
    if not hasattr(langchain, 'llm_cache'):
        # Set llm_cache to None (disabled cache)
        # This is compatible with LangChain's cache interface
        langchain.llm_cache = None
except ImportError:
    # langchain not installed, skip
    pass

