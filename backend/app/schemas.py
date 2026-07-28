"""
Pydantic schemas used at the API boundary.

Kept separate from the ORM models (app.models) so the DB layer and the API
contract can evolve independently.
"""
import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class ChatMessage(BaseModel):
    """One turn in a complaint's copilot conversation."""
    role: str  # "user" | "assistant"
    content: str
    attachment_name: Optional[str] = None


class ComplaintResponse(BaseModel):
    """Full complaint record — drives both the Log Customer Complaint form
    and the AI Risk Assessment section from a single response shape."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID

    complaint_source: Optional[str] = None
    customer_name: Optional[str] = None

    product_name: Optional[str] = None
    product_strength: Optional[str] = None
    batch_number: Optional[str] = None
    affected_quantity: Optional[str] = None
    manufacturing_date: Optional[str] = None
    expiry_date: Optional[str] = None

    manufacturing_site: Optional[str] = None
    material_type: Optional[str] = None

    complaint_date: Optional[str] = None
    complaint_description: Optional[str] = None
    complaint_category: Optional[str] = None

    completeness_score: Optional[float] = None
    missing_fields: Optional[list[str]] = None
    risk_level: str
    risk_justification: Optional[str] = None
    root_cause_suggestions: Optional[list[str]] = None
    capa_recommendations: Optional[list[str]] = None
    ai_summary: Optional[str] = None
    is_possible_duplicate: bool = False
    duplicate_of: Optional[uuid.UUID] = None
    duplicate_reason: Optional[str] = None

    status: str
    chat_history: Optional[list[ChatMessage]] = None

    created_at: datetime
    updated_at: datetime


class ComplaintListItem(BaseModel):
    """Lightweight shape used for the complaints log table."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    product_name: Optional[str] = None
    customer_name: Optional[str] = None
    risk_level: str
    status: str
    created_at: datetime


class CopilotMessageResponse(BaseModel):
    """What the copilot chat endpoint returns after running a tool."""

    complaint: ComplaintResponse
    assistant_reply: str
    tool_used: str  # "log_complaint" | "edit_complaint" | "document_extraction"
    changed_fields: Optional[list[str]] = None  # which form fields this turn touched
