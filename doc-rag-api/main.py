# LangChain compatibility fix - must be imported first
import langchain_compat  # noqa: F401

from fastapi import FastAPI, UploadFile, File, HTTPException, Form
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from bson import ObjectId
import logging
import shutil

from config import settings
from database import connect_to_mongo, close_mongo_connection, get_database
from vectorstore import vector_store
from doc_ingest import index_document
from doc_summary import summarize_document, SummaryType
from rag_graph import rag_app
from models import (
    DocumentUploadResponse,
    DocumentResponse,
    DocumentListResponse,
    SummaryRequest,
    SummaryResponse,
    ChatRequest,
    ChatResponse
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events"""
    # Startup
    logger.info("Starting up Document RAG Service...")
    await connect_to_mongo()
    vector_store.initialize()
    logger.info("Service ready!")
    
    yield
    
    # Shutdown
    logger.info("Shutting down...")
    await close_mongo_connection()


app = FastAPI(
    title="Court Document RAG API",
    description="RAG-based document processing and chat API for legal documents",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "service": "Court Document RAG API",
        "status": "running",
        "version": "1.0.0"
    }


@app.post("/documents/", response_model=DocumentUploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    case_id: str = Form(None)
):
    """Upload and index a document (PDF, DOCX, or TXT)"""
    try:
        # Validate file type
        allowed_extensions = {'.pdf', '.docx', '.doc', '.txt'}
        file_ext = Path(file.filename).suffix.lower()
        
        if file_ext not in allowed_extensions:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file type. Allowed: {', '.join(allowed_extensions)}"
            )
        
        # Generate unique filename
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        safe_filename = f"{timestamp}_{file.filename}"
        file_path = Path(settings.upload_dir) / safe_filename
        
        # Save file to disk
        with file_path.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        logger.info(f"Saved file: {safe_filename}")
        
        # Insert document record in MongoDB
        db = get_database()
        doc_record = {
            "filename": file.filename,
            "local_path": str(file_path),
            "case_id": case_id,
            "uploaded_at": datetime.utcnow(),
            "summary_brief": None,
            "summary_detailed": None,
            "summary_key_points": None
        }
        
        result = await db.documents.insert_one(doc_record)
        doc_id = str(result.inserted_id)
        
        logger.info(f"Created document record with ID: {doc_id}")
        
        # Index document in FAISS
        success = index_document(str(file_path), doc_id, case_id)
        
        if not success:
            file_path.unlink(missing_ok=True)
            await db.documents.delete_one({"_id": result.inserted_id})
            raise HTTPException(status_code=500, detail="Failed to index document")
        
        return DocumentUploadResponse(
            id=doc_id,
            filename=file.filename,
            message="Document uploaded and indexed successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading document: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/documents/", response_model=DocumentListResponse)
async def list_documents(case_id: str = None):
    """List all documents, optionally filtered by case_id"""
    try:
        db = get_database()
        query = {}
        if case_id:
            query["case_id"] = case_id
        
        cursor = db.documents.find(query).sort("uploaded_at", -1)
        documents = await cursor.to_list(length=None)
        
        doc_list = []
        for doc in documents:
            doc_list.append(DocumentResponse(
                id=str(doc["_id"]),
                filename=doc["filename"],
                case_id=doc.get("case_id"),
                uploaded_at=doc["uploaded_at"],
                summary_brief=doc.get("summary_brief"),
                summary_detailed=doc.get("summary_detailed"),
                summary_key_points=doc.get("summary_key_points")
            ))
        
        return DocumentListResponse(documents=doc_list, total=len(doc_list))
        
    except Exception as e:
        logger.error(f"Error listing documents: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/documents/{doc_id}", response_model=DocumentResponse)
async def get_document(doc_id: str):
    """Get a single document's metadata"""
    try:
        db = get_database()
        
        if not ObjectId.is_valid(doc_id):
            raise HTTPException(status_code=400, detail="Invalid document ID")
        
        doc = await db.documents.find_one({"_id": ObjectId(doc_id)})
        
        if not doc:
            raise HTTPException(status_code=404, detail="Document not found")
        
        return DocumentResponse(
            id=str(doc["_id"]),
            filename=doc["filename"],
            case_id=doc.get("case_id"),
            uploaded_at=doc["uploaded_at"],
            summary_brief=doc.get("summary_brief"),
            summary_detailed=doc.get("summary_detailed"),
            summary_key_points=doc.get("summary_key_points")
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching document {doc_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/documents/{doc_id}/summary", response_model=SummaryResponse)
async def generate_summary(doc_id: str, request: SummaryRequest):
    """Generate a summary for a document"""
    try:
        db = get_database()
        
        if not ObjectId.is_valid(doc_id):
            raise HTTPException(status_code=400, detail="Invalid document ID")
        
        doc = await db.documents.find_one({"_id": ObjectId(doc_id)})
        if not doc:
            raise HTTPException(status_code=404, detail="Document not found")
        
        # Check cache
        cache_field = f"summary_{request.summary_type}"
        cached_summary = doc.get(cache_field)
        
        if cached_summary:
            logger.info(f"Returning cached {request.summary_type} summary")
            return SummaryResponse(
                doc_id=doc_id,
                summary_type=request.summary_type,
                summary=cached_summary
            )
        
        # Generate new summary
        summary = summarize_document(doc_id, request.summary_type)
        
        # Cache in MongoDB
        await db.documents.update_one(
            {"_id": ObjectId(doc_id)},
            {"$set": {cache_field: summary}}
        )
        
        logger.info(f"Generated and cached {request.summary_type} summary")
        
        return SummaryResponse(
            doc_id=doc_id,
            summary_type=request.summary_type,
            summary=summary
        )
        
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error generating summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/documents/chat", response_model=ChatResponse)
async def chat_with_document(request: ChatRequest):
    """Chat with a document using RAG"""
    try:
        db = get_database()
        
        if not ObjectId.is_valid(request.doc_id):
            raise HTTPException(status_code=400, detail="Invalid document ID")
        
        doc = await db.documents.find_one({"_id": ObjectId(request.doc_id)})
        if not doc:
            raise HTTPException(status_code=404, detail="Document not found")
        
        if not vector_store.index_exists(request.doc_id):
            raise HTTPException(
                status_code=400,
                detail="Document not indexed. Please re-upload."
            )
        
        # Invoke RAG workflow
        result = rag_app.invoke({
            "question": request.message,
            "doc_id": request.doc_id,
            "context_docs": [],
            "answer": ""
        })
        
        return ChatResponse(
            answer=result["answer"],
            doc_id=request.doc_id
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in chat: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/documents/{doc_id}")
async def delete_document(doc_id: str):
    """Delete a document and its associated data"""
    try:
        db = get_database()
        
        if not ObjectId.is_valid(doc_id):
            raise HTTPException(status_code=400, detail="Invalid document ID")
        
        doc = await db.documents.find_one({"_id": ObjectId(doc_id)})
        if not doc:
            raise HTTPException(status_code=404, detail="Document not found")
        
        # Delete file
        file_path = Path(doc["local_path"])
        if file_path.exists():
            file_path.unlink()
        
        # Delete FAISS index
        vector_store.delete_vectorstore(doc_id)
        
        # Delete from MongoDB
        await db.documents.delete_one({"_id": ObjectId(doc_id)})
        
        logger.info(f"Deleted document: {doc_id}")
        
        return {"message": "Document deleted successfully", "doc_id": doc_id}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting document: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=True
    )