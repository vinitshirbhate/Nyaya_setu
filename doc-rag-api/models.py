from pydantic import BaseModel, Field
from typing import Optional, Literal
from datetime import datetime
from bson import ObjectId


class PyObjectId(ObjectId):
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v):
        if not ObjectId.is_valid(v):
            raise ValueError("Invalid ObjectId")
        return ObjectId(v)

    @classmethod
    def __get_pydantic_json_schema__(cls, schema):
        schema.update(type="string")
        return schema


# Request Models
class SummaryRequest(BaseModel):
    summary_type: Literal["brief", "detailed", "key_points"]


class ChatRequest(BaseModel):
    doc_id: Optional[str] = None
    doc_ids: Optional[list[str]] = None
    message: str


# Response Models
class DocumentUploadResponse(BaseModel):
    id: str
    filename: str
    message: str


class DocumentResponse(BaseModel):
    id: str
    filename: str
    case_id: Optional[str] = None
    uploaded_at: datetime
    summary_brief: Optional[str] = None
    summary_detailed: Optional[str] = None
    summary_key_points: Optional[str] = None


class DocumentListResponse(BaseModel):
    documents: list[DocumentResponse]
    total: int


class SummaryResponse(BaseModel):
    doc_id: str
    summary_type: str
    summary: str


class CombinedSummaryRequest(BaseModel):
    doc_ids: list[str]
    summary_type: Literal["brief", "detailed", "key_points"]


class CombinedSummaryResponse(BaseModel):
    doc_ids: list[str]
    summary_type: str
    summary: str


class ChatResponse(BaseModel):
    answer: str
    doc_id: str


# Database Models
class DocumentDB(BaseModel):
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    filename: str
    local_path: str
    case_id: Optional[str] = None
    uploaded_at: datetime = Field(default_factory=datetime.utcnow)
    summary_brief: Optional[str] = None
    summary_detailed: Optional[str] = None
    summary_key_points: Optional[str] = None

    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}