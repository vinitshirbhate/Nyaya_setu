# LangChain compatibility fix - must be imported first
import langchain_compat  # noqa: F401

from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document
from typing import List, Optional
from pathlib import Path
from config import settings
import logging
import pickle

logger = logging.getLogger(__name__)


class VectorStore:
    def __init__(self):
        self.embeddings = None
        self._initialized = False
        self.index_path = Path(settings.faiss_index_dir)
    
    def initialize(self):
        """Initialize embeddings"""
        if self._initialized:
            return
        
        try:
            self.embeddings = GoogleGenerativeAIEmbeddings(
                model="models/text-embedding-004",
                google_api_key=settings.gemini_api_key
            )
            
            self._initialized = True
            logger.info("Vector store initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize vector store: {e}")
            raise
    
    def _get_index_path(self, doc_id: str) -> Path:
        """Get the path for a document's FAISS index"""
        return self.index_path / f"doc_{doc_id}.faiss"
    
    def _get_docstore_path(self, doc_id: str) -> Path:
        """Get the path for a document's docstore pickle"""
        return self.index_path / f"doc_{doc_id}.pkl"
    
    def create_vectorstore(self, documents: List[Document], doc_id: str) -> FAISS:
        """Create and save a new FAISS vectorstore for a document"""
        if not self._initialized:
            self.initialize()
        
        try:
            # Create FAISS index from documents
            vectorstore = FAISS.from_documents(
                documents=documents,
                embedding=self.embeddings
            )
            
            # Save to disk
            index_file = str(self._get_index_path(doc_id))
            vectorstore.save_local(index_file)
            
            logger.info(f"Created and saved FAISS index for doc_id: {doc_id}")
            return vectorstore
            
        except Exception as e:
            logger.error(f"Error creating vectorstore for doc_id {doc_id}: {e}")
            raise
    
    def load_vectorstore(self, doc_id: str) -> Optional[FAISS]:
        """Load an existing FAISS vectorstore for a document"""
        if not self._initialized:
            self.initialize()
        
        index_file = str(self._get_index_path(doc_id))
        
        if not Path(index_file).exists():
            logger.warning(f"No FAISS index found for doc_id: {doc_id}")
            return None
        
        try:
            vectorstore = FAISS.load_local(
                index_file,
                embeddings=self.embeddings,
                allow_dangerous_deserialization=True
            )
            logger.info(f"Loaded FAISS index for doc_id: {doc_id}")
            return vectorstore
            
        except Exception as e:
            logger.error(f"Error loading vectorstore for doc_id {doc_id}: {e}")
            raise
    
    def delete_vectorstore(self, doc_id: str) -> bool:
        """Delete a document's FAISS index"""
        try:
            index_file = self._get_index_path(doc_id)
            docstore_file = self._get_docstore_path(doc_id)
            
            deleted = False
            if index_file.exists():
                index_file.unlink()
                deleted = True
            
            if docstore_file.exists():
                docstore_file.unlink()
                deleted = True
            
            if deleted:
                logger.info(f"Deleted FAISS index for doc_id: {doc_id}")
            return deleted
            
        except Exception as e:
            logger.error(f"Error deleting vectorstore for doc_id {doc_id}: {e}")
            return False
    
    def index_exists(self, doc_id: str) -> bool:
        """Check if a FAISS index exists for a document"""
        return self._get_index_path(doc_id).exists()


# Global instance
vector_store = VectorStore()