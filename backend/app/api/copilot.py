"""
The AIVOA Copilot chat endpoint — the single entry point for all three
required AI tools. Which tool runs is decided deterministically from the
shape of the request (see graph.py's routing comment for the rationale):

  - a PDF file is attached                       -> Document Extraction Tool
  - no file, but `complaint_id` is provided       -> Edit Complaint Tool
  - no file, no `complaint_id`                    -> Log Complaint Tool

Every turn re-runs the full risk-assessment pipeline (completeness, risk
classification, root cause, CAPA, duplicate check, summary) against the
complaint's current state, so the AI Risk Assessment panel is always in
sync with whatever is now in the form — including after an edit.
"""
import logging
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.database import get_db
from app.models import Complaint
from app.schemas import CopilotMessageResponse
from app.agents.graph import copilot_graph
from app.agents.nodes import FORM_FIELDS
from app.utils.document_parser import extract_text_from_pdf

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/copilot", tags=["copilot"])

DUPLICATE_CHECK_WINDOW = 25


def _complaint_to_field_dict(complaint: Complaint) -> dict:
    return {f: getattr(complaint, f) for f in FORM_FIELDS}


def _recent_complaints_for_dup_check(db: Session, exclude_id: Optional[uuid.UUID]) -> list[dict]:
    query = db.query(Complaint.id, Complaint.product_name, Complaint.complaint_description)
    if exclude_id:
        query = query.filter(Complaint.id != exclude_id)
    rows = query.order_by(desc(Complaint.created_at)).limit(DUPLICATE_CHECK_WINDOW).all()
    return [
        {"id": str(r.id), "product_name": r.product_name, "complaint_description": r.complaint_description}
        for r in rows
    ]


@router.post("/message", response_model=CopilotMessageResponse, status_code=200)
async def send_copilot_message(
    db: Session = Depends(get_db),
    message: Optional[str] = Form(None),
    complaint_id: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None),
):
    if not message and not file:
        raise HTTPException(status_code=422, detail="Provide a message, a file, or both.")

    existing_complaint: Optional[Complaint] = None
    if complaint_id:
        try:
            complaint_uuid = uuid.UUID(complaint_id)
        except ValueError:
            raise HTTPException(status_code=422, detail="complaint_id is not a valid UUID.")
        existing_complaint = db.query(Complaint).filter(Complaint.id == complaint_uuid).first()
        if not existing_complaint:
            raise HTTPException(status_code=404, detail="complaint_id does not match any complaint.")

    # --- determine mode + build the LangGraph initial state ---
    initial_state: dict = {"user_message": message}

    if file is not None:
        if file.content_type != "application/pdf":
            raise HTTPException(status_code=415, detail="Only PDF uploads are supported in this demo.")
        file_bytes = await file.read()
        try:
            initial_state["document_text"] = extract_text_from_pdf(file_bytes)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        initial_state["mode"] = "extract_document"
    elif existing_complaint is not None:
        initial_state["mode"] = "edit"
        initial_state["existing_complaint"] = _complaint_to_field_dict(existing_complaint)
    else:
        initial_state["mode"] = "log"

    initial_state["existing_complaints_for_dup_check"] = _recent_complaints_for_dup_check(
        db, exclude_id=existing_complaint.id if existing_complaint else None
    )

    # --- run the agent ---
    try:
        result_state = copilot_graph.invoke(initial_state)
    except Exception as exc:  # noqa: BLE001
        logger.exception("Copilot AI workflow failed")
        raise HTTPException(status_code=502, detail=f"AI processing failed: {exc}") from exc

    # --- persist ---
    user_turn = {"role": "user", "content": message or "", "attachment_name": file.filename if file else None}
    assistant_turn = {"role": "assistant", "content": result_state.get("assistant_reply", "")}

    duplicate_of = result_state.get("duplicate_of")
    field_values = {f: result_state.get(f) for f in FORM_FIELDS}
    risk_fields = dict(
        completeness_score=result_state.get("completeness_score"),
        missing_fields=result_state.get("missing_fields"),
        risk_level=result_state.get("risk_level", "Unclassified"),
        risk_justification=result_state.get("risk_justification"),
        root_cause_suggestions=result_state.get("root_cause_suggestions"),
        capa_recommendations=result_state.get("capa_recommendations"),
        ai_summary=result_state.get("ai_summary"),
        is_possible_duplicate=result_state.get("is_possible_duplicate", False),
        duplicate_of=uuid.UUID(duplicate_of) if duplicate_of else None,
        duplicate_reason=result_state.get("duplicate_reason"),
    )

    if existing_complaint is not None:
        for k, v in {**field_values, **risk_fields}.items():
            setattr(existing_complaint, k, v)
        existing_complaint.chat_history = (existing_complaint.chat_history or []) + [user_turn, assistant_turn]
        if (existing_complaint.completeness_score or 0) >= 100:
            existing_complaint.status = "Ready to Commit"
        complaint = existing_complaint
    else:
        complaint = Complaint(
            **field_values,
            **risk_fields,
            chat_history=[user_turn, assistant_turn],
            status="Ready to Commit" if (risk_fields["completeness_score"] or 0) >= 100 else "Draft",
        )
        db.add(complaint)

    db.commit()
    db.refresh(complaint)

    return CopilotMessageResponse(
        complaint=complaint,
        assistant_reply=result_state.get("assistant_reply", ""),
        tool_used={"log": "log_complaint", "edit": "edit_complaint", "extract_document": "document_extraction"}[
            initial_state["mode"]
        ],
        changed_fields=result_state.get("changed_fields"),
    )
