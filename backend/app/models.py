"""
ORM models.

`Complaint` mirrors the full "Log Customer Complaint" form (origin/customer,
product/batch, facility/material impact) plus every field the AI Copilot
populates (completeness, risk, root cause, CAPA, summary, duplicate flag).
Keeping the whole record on one row means a single API response can drive
both the form and the risk-assessment display, and both the Log/Edit/
Document-Extraction tools all write to the same shape.
"""
import enum
import uuid
from datetime import datetime

from sqlalchemy import Column, String, Text, DateTime, Enum, Float, Boolean, JSON
from sqlalchemy.dialects.postgresql import UUID

from app.database import Base


class RiskLevel(str, enum.Enum):
    CRITICAL = "Critical"
    MAJOR = "Major"
    MINOR = "Minor"
    UNCLASSIFIED = "Unclassified"


class ComplaintStatus(str, enum.Enum):
    DRAFT = "Draft"  # copilot is still gathering info / mid-conversation
    READY_TO_COMMIT = "Ready to Commit"  # completeness score is high enough to file
    UNDER_REVIEW = "Under Review"
    CLOSED = "Closed"


class Complaint(Base):
    __tablename__ = "complaints"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # --- Section 1: Origin & Customer Details ---
    complaint_source = Column(String(50), nullable=True)  # Email | Phone | Portal | Letter | Other
    customer_name = Column(String(255), nullable=True)

    # --- Section 2: Product & Batch Identification ---
    product_name = Column(String(255), nullable=True)
    product_strength = Column(String(100), nullable=True)  # e.g. "500mg", "IP/BP"
    batch_number = Column(String(100), nullable=True)
    affected_quantity = Column(String(100), nullable=True)  # free text: "48 capsules", "25 kg (1 drum)"
    manufacturing_date = Column(String(50), nullable=True)
    expiry_date = Column(String(50), nullable=True)

    # --- Section 3: Facility & Material Impact ---
    manufacturing_site = Column(String(255), nullable=True)
    material_type = Column(String(20), nullable=True)  # API | FDF

    # --- Narrative ---
    complaint_date = Column(String(50), nullable=True)  # date the complaint was reported
    complaint_description = Column(Text, nullable=True)
    complaint_category = Column(String(100), nullable=True)  # Quality Defect, Packaging, Adverse Event, ...

    # --- AI Copilot: risk assessment & QMS triage ---
    completeness_score = Column(Float, nullable=True)  # 0-100
    missing_fields = Column(JSON, nullable=True)  # list[str]
    risk_level = Column(Enum(RiskLevel), default=RiskLevel.UNCLASSIFIED)
    risk_justification = Column(Text, nullable=True)
    root_cause_suggestions = Column(JSON, nullable=True)  # list[str]
    capa_recommendations = Column(JSON, nullable=True)  # list[str]
    ai_summary = Column(Text, nullable=True)
    is_possible_duplicate = Column(Boolean, default=False)
    duplicate_of = Column(UUID(as_uuid=True), nullable=True)
    duplicate_reason = Column(Text, nullable=True)

    status = Column(Enum(ComplaintStatus), default=ComplaintStatus.DRAFT)

    # --- Conversation history for this complaint's copilot thread ---
    # Stored as a JSON list of {role, content, attachment_name} so the chat
    # panel can be reloaded/rehydrated. Kept simple (no separate table)
    # since a complaint has exactly one copilot thread in this demo.
    chat_history = Column(JSON, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
