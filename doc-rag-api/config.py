from pydantic_settings import BaseSettings
from pathlib import Path


class Settings(BaseSettings):
    # MongoDB
    mongo_uri: str = "mongodb+srv://vinitshirbhate_db_user:bfOmEp2aRbZX3UST@cluster0.mx9ptq8.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
    mongo_db_name: str = "court_docs_db"
    
    # Google Gemini
    gemini_api_key: str
    
    # Server
    host: str = "0.0.0.0"
    port: int = 8001
    
    # Storage
    upload_dir: str = "./uploads/docs"
    faiss_index_dir: str = "./faiss_indexes"
    
    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()

# Ensure directories exist
Path(settings.upload_dir).mkdir(parents=True, exist_ok=True)
Path(settings.faiss_index_dir).mkdir(parents=True, exist_ok=True)