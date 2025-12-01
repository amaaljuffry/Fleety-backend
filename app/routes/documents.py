from fastapi import APIRouter, Depends, HTTPException, status, Header, UploadFile, File, Form
from fastapi.responses import FileResponse, StreamingResponse
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime
import os
import uuid
import shutil
from pathlib import Path

from app.database import get_database
from app.models.document import Document
from app.models.vehicle import Vehicle
from app.utils.auth import decode_token

router = APIRouter(prefix="/api/documents", tags=["documents"])

# Configure upload directory
UPLOAD_DIR = Path("uploads/documents")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# Allowed file types
ALLOWED_EXTENSIONS = {
    ".pdf", ".jpg", ".jpeg", ".png", ".gif", ".webp",
    ".doc", ".docx", ".xls", ".xlsx"
}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB


# Pydantic schemas
class DocumentResponse(BaseModel):
    id: str
    vehicle_id: str
    document_type: str
    title: Optional[str] = None
    description: Optional[str] = None
    file_name: str
    file_url: str
    file_size: int
    mime_type: Optional[str] = None
    expiry_date: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class DocumentUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    document_type: Optional[str] = None
    expiry_date: Optional[datetime] = None


def get_current_user_id(authorization: str = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated"
        )
    
    token = authorization.replace("Bearer ", "")
    payload = decode_token(token)
    
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )
    
    return payload.get("sub")


def validate_file(file: UploadFile):
    """Validate uploaded file"""
    # Check file extension
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File type not allowed. Allowed types: {', '.join(ALLOWED_EXTENSIONS)}"
        )
    
    return ext


@router.post("/vehicle/{vehicle_id}", response_model=DocumentResponse)
async def upload_document(
    vehicle_id: str,
    file: UploadFile = File(...),
    document_type: str = Form(default="other"),
    title: Optional[str] = Form(default=None),
    description: Optional[str] = Form(default=None),
    expiry_date: Optional[str] = Form(default=None),
    user_id: str = Depends(get_current_user_id),
    db=Depends(get_database)
):
    """Upload a document for a vehicle"""
    # Verify vehicle exists and belongs to user
    vehicle_model = Vehicle(db)
    vehicle = vehicle_model.get_by_id(vehicle_id, user_id)
    if not vehicle:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vehicle not found"
        )
    
    # Validate file
    ext = validate_file(file)
    
    # Generate unique filename
    unique_filename = f"{uuid.uuid4()}{ext}"
    file_path = UPLOAD_DIR / unique_filename
    
    # Save file
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Get file size
        file_size = os.path.getsize(file_path)
        
        if file_size > MAX_FILE_SIZE:
            os.remove(file_path)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File too large. Maximum size is {MAX_FILE_SIZE // (1024*1024)}MB"
            )
    except Exception as e:
        if file_path.exists():
            os.remove(file_path)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save file: {str(e)}"
        )
    
    # Parse expiry date if provided
    parsed_expiry = None
    if expiry_date:
        try:
            parsed_expiry = datetime.fromisoformat(expiry_date.replace("Z", "+00:00"))
        except ValueError:
            pass
    
    # Create document record
    document_model = Document(db)
    document_data = {
        "document_type": document_type,
        "title": title or file.filename,
        "description": description,
        "file_name": file.filename,
        "file_url": f"/api/documents/file/{unique_filename}",
        "file_size": file_size,
        "mime_type": file.content_type,
        "expiry_date": parsed_expiry,
    }
    
    created_document = document_model.create(user_id, vehicle_id, document_data)
    return created_document


@router.get("/vehicle/{vehicle_id}", response_model=List[DocumentResponse])
async def get_vehicle_documents(
    vehicle_id: str,
    user_id: str = Depends(get_current_user_id),
    db=Depends(get_database)
):
    """Get all documents for a vehicle"""
    # Verify vehicle exists and belongs to user
    vehicle_model = Vehicle(db)
    vehicle = vehicle_model.get_by_id(vehicle_id, user_id)
    if not vehicle:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vehicle not found"
        )
    
    document_model = Document(db)
    documents = document_model.get_by_vehicle(vehicle_id, user_id)
    return documents


@router.get("/all", response_model=List[DocumentResponse])
async def get_all_documents(
    user_id: str = Depends(get_current_user_id),
    db=Depends(get_database)
):
    """Get all documents for the current user"""
    document_model = Document(db)
    documents = document_model.get_all_by_user(user_id)
    return documents


@router.get("/expiring", response_model=List[DocumentResponse])
async def get_expiring_documents(
    days: int = 30,
    user_id: str = Depends(get_current_user_id),
    db=Depends(get_database)
):
    """Get documents expiring within specified days"""
    document_model = Document(db)
    documents = document_model.get_expiring_soon(user_id, days)
    return documents


@router.get("/file/{filename}")
async def get_document_file(filename: str):
    """Serve a document file"""
    file_path = UPLOAD_DIR / filename
    
    if not file_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found"
        )
    
    return FileResponse(file_path)


@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: str,
    user_id: str = Depends(get_current_user_id),
    db=Depends(get_database)
):
    """Get a specific document by ID"""
    document_model = Document(db)
    document = document_model.get_by_id(document_id, user_id)
    
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )
    
    return document


@router.put("/{document_id}", response_model=DocumentResponse)
async def update_document(
    document_id: str,
    update_data: DocumentUpdate,
    user_id: str = Depends(get_current_user_id),
    db=Depends(get_database)
):
    """Update document metadata"""
    document_model = Document(db)
    
    # Check if document exists
    existing = document_model.get_by_id(document_id, user_id)
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )
    
    # Update document
    update_dict = {k: v for k, v in update_data.dict().items() if v is not None}
    updated = document_model.update(document_id, user_id, update_dict)
    
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update document"
        )
    
    return updated


@router.delete("/{document_id}")
async def delete_document(
    document_id: str,
    user_id: str = Depends(get_current_user_id),
    db=Depends(get_database)
):
    """Delete a document"""
    document_model = Document(db)
    
    # Get document to find file path
    document = document_model.get_by_id(document_id, user_id)
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )
    
    # Delete file from disk
    try:
        filename = document["file_url"].split("/")[-1]
        file_path = UPLOAD_DIR / filename
        if file_path.exists():
            os.remove(file_path)
    except Exception:
        pass  # Continue even if file deletion fails
    
    # Delete database record
    deleted = document_model.delete(document_id, user_id)
    
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete document"
        )
    
    return {"message": "Document deleted successfully"}


@router.get("/types/list")
async def get_document_types():
    """Get list of available document types"""
    return {
        "types": [
            {"value": "insurance", "label": "Insurance"},
            {"value": "registration", "label": "Registration"},
            {"value": "inspection", "label": "Inspection Certificate"},
            {"value": "service_receipt", "label": "Service Receipt"},
            {"value": "other", "label": "Other"},
        ]
    }
