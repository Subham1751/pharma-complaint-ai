"""
Read-only complaint endpoints, used by the Complaint Log table.

Creating/editing complaints happens through the conversational copilot
endpoint (see app/api/copilot.py) — that's the single entry point for all
three AI tools (Log, Edit, Document Extraction).
"""
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.database import get_db
from app.models import Complaint
from app.schemas import ComplaintResponse, ComplaintListItem

router = APIRouter(prefix="/complaints", tags=["complaints"])


@router.get("/", response_model=list[ComplaintListItem])
def list_complaints(db: Session = Depends(get_db)):
    """List complaints, most recent first, for the complaint log table."""
    return db.query(Complaint).order_by(desc(Complaint.created_at)).all()


@router.get("/{complaint_id}", response_model=ComplaintResponse)
def get_complaint(complaint_id: uuid.UUID, db: Session = Depends(get_db)):
    """Fetch a single complaint, including its chat history and AI fields.

    Used when a user reopens a past complaint from the log to continue
    editing it via the copilot.
    """
    complaint = db.query(Complaint).filter(Complaint.id == complaint_id).first()
    if not complaint:
        raise HTTPException(status_code=404, detail="Complaint not found.")
    return complaint
