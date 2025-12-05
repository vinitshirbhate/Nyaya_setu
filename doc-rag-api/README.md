# Document RAG API

A FastAPI-based service for document processing, summarization, and RAG (Retrieval-Augmented Generation) chat functionality.

## Quick Start

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Set up environment variables in `.env`:
```
GEMINI_API_KEY=your_api_key_here
```

3. Run the server:
```bash
python main.py
```

The API will be available at `http://localhost:8001`

## Interactive API Documentation

FastAPI automatically provides interactive API documentation:

- **Swagger UI**: `http://localhost:8001/docs`
- **ReDoc**: `http://localhost:8001/redoc`
- **OpenAPI Schema**: `http://localhost:8001/openapi.json`

## API Endpoints Quick Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | Health check |
| POST | `/documents/` | Upload and index a document |
| GET | `/documents/` | List all documents (optional: `?case_id=...`) |
| GET | `/documents/{doc_id}` | Get document metadata |
| POST | `/documents/{doc_id}/summary` | Generate document summary |
| POST | `/documents/chat` | Chat with document using RAG |
| DELETE | `/documents/{doc_id}` | Delete document |

## Detailed API Documentation

See [API_ENDPOINTS.md](./API_ENDPOINTS.md) for complete endpoint documentation with request/response examples and frontend integration code.

## Features

- Document upload and indexing (PDF, DOCX, TXT)
- Multiple summary types (brief, detailed, key points)
- RAG-based document chat
- Case-based document organization
- Vector search using FAISS
- MongoDB for document metadata storage

## Tech Stack

- FastAPI
- MongoDB (via Motor)
- FAISS (vector search)
- LangChain & LangGraph
- Google Gemini AI
- Python 3.8+

