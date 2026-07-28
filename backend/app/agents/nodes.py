"""
LangGraph nodes for the AIVOA Copilot agent.

Three "tools" (each a small subgraph of nodes) feed into one shared risk-
assessment pipeline, so the form and the AI Risk Assessment section are
always recomputed from the complaint's full current state — whether that
state just came from a fresh extraction, a document upload, or a natural-
language edit:

  Log Complaint Tool          -> extract_from_message_node
  Document Extraction Tool    -> extract_from_document_node
  Edit Complaint Tool         -> apply_edit_node
                                        |
                                        v
                              completeness_check_node
                                        v
                              risk_classification_node
                                        v
                              root_cause_node
                                        v
                              capa_node
                                        v
                              duplicate_detection_node
                                        v
                              summarize_node
                                        v
                              generate_reply_node   (chat-facing confirmation)
"""
import logging
from typing import TypedDict, Optional

from app.agents.llm import call_llm_json

logger = logging.getLogger(__name__)

# Fields the "Log Customer Complaint" form expects filled in before a
# complaint is considered ready to file. Used by the completeness checker.
REQUIRED_FIELDS = [
    "customer_name",
    "product_name",
    "batch_number",
    "affected_quantity",
    "manufacturing_date",
    "complaint_description",
]

# All form fields the extraction/edit tools are allowed to populate.
FORM_FIELDS = [
    "complaint_source",
    "customer_name",
    "product_name",
    "product_strength",
    "batch_number",
    "affected_quantity",
    "manufacturing_date",
    "expiry_date",
    "manufacturing_site",
    "material_type",
    "complaint_date",
    "complaint_description",
    "complaint_category",
]


class CopilotState(TypedDict, total=False):
    # --- routing input ---
    mode: str  # "log" | "edit" | "extract_document"
    user_message: Optional[str]  # natural-language chat prompt
    document_text: Optional[str]  # extracted PDF text, if a file was attached
    existing_complaint: Optional[dict]  # current field values, for edit mode
    existing_complaints_for_dup_check: list[dict]

    # --- form fields (see FORM_FIELDS) ---
    complaint_source: Optional[str]
    customer_name: Optional[str]
    product_name: Optional[str]
    product_strength: Optional[str]
    batch_number: Optional[str]
    affected_quantity: Optional[str]
    manufacturing_date: Optional[str]
    expiry_date: Optional[str]
    manufacturing_site: Optional[str]
    material_type: Optional[str]
    complaint_date: Optional[str]
    complaint_description: Optional[str]
    complaint_category: Optional[str]

    # --- risk assessment output ---
    completeness_score: float
    missing_fields: list[str]
    risk_level: str
    risk_justification: str
    root_cause_suggestions: list[str]
    capa_recommendations: list[str]
    is_possible_duplicate: bool
    duplicate_of: Optional[str]
    duplicate_reason: Optional[str]
    ai_summary: str

    # --- chat output ---
    changed_fields: list[str]  # which fields this turn touched (used by generate_reply)
    assistant_reply: str


# ---------------------------------------------------------------------------
# Tool 1: Log Complaint — extract structured fields from a natural-language
# chat prompt describing a brand-new complaint.
# ---------------------------------------------------------------------------
def extract_from_message_node(state: CopilotState) -> dict:
    system_prompt = (
        "You are a pharmaceutical QMS data-entry assistant. A user is describing a NEW "
        "customer complaint in natural language (it may be a full narrative or just a few "
        "facts). Extract whatever structured fields are mentioned; use null for anything not "
        "stated — do not guess or invent values. Respond as a single JSON object with exactly "
        "these keys: complaint_source (Email|Phone|Portal|Letter|Other), customer_name, "
        "product_name, product_strength, batch_number, affected_quantity, manufacturing_date, "
        "expiry_date, manufacturing_site, material_type (API|FDF), complaint_date, "
        "complaint_description (a clean 1-2 sentence restatement of the issue), "
        "complaint_category (Quality Defect|Packaging|Adverse Event|Labeling|Efficacy|"
        "Delivery/Logistics|Other)."
    )
    result = call_llm_json(system_prompt, state.get("user_message") or "")
    update = {f: result.get(f) for f in FORM_FIELDS}
    if not update.get("complaint_description"):
        update["complaint_description"] = state.get("user_message")
    update["changed_fields"] = [f for f in FORM_FIELDS if update.get(f)]
    return update


# ---------------------------------------------------------------------------
# Tool 2: Document Extraction — same idea, but the source is text pulled
# from an uploaded PDF/email rather than a typed chat message.
# ---------------------------------------------------------------------------
def extract_from_document_node(state: CopilotState) -> dict:
    system_prompt = (
        "You are a pharmaceutical QMS data-entry assistant. The following text was extracted "
        "from an uploaded complaint document (PDF or email). Extract structured fields; use "
        "null for anything not stated. Respond as a single JSON object with exactly these "
        "keys: complaint_source (Email|Phone|Portal|Letter|Other — infer 'Email' if it reads "
        "like an email), customer_name, product_name, product_strength, batch_number, "
        "affected_quantity, manufacturing_date, expiry_date, manufacturing_site, "
        "material_type (API|FDF), complaint_date, complaint_description (a clean 1-2 sentence "
        "restatement of the issue), complaint_category (Quality Defect|Packaging|Adverse Event|"
        "Labeling|Efficacy|Delivery/Logistics|Other)."
    )
    document_text = state.get("document_text") or ""
    # If the user also typed a note alongside the upload, give the model that context too.
    user_note = state.get("user_message")
    user_prompt = f"{document_text}\n\n---\nUser's accompanying note: {user_note}" if user_note else document_text

    result = call_llm_json(system_prompt, user_prompt)
    update = {f: result.get(f) for f in FORM_FIELDS}
    if not update.get("complaint_description"):
        update["complaint_description"] = document_text[:500]
    update["changed_fields"] = [f for f in FORM_FIELDS if update.get(f)]
    return update


# ---------------------------------------------------------------------------
# Tool 3: Edit Complaint — apply a natural-language correction to an
# existing complaint, changing only what the user actually asked to change
# and preserving everything else.
# ---------------------------------------------------------------------------
def apply_edit_node(state: CopilotState) -> dict:
    existing = state.get("existing_complaint") or {}
    system_prompt = (
        "You are a pharmaceutical QMS data-entry assistant. The user is correcting or adding "
        "to a complaint that has already been logged. You are given the CURRENT field values "
        "and a natural-language instruction. Return ONLY the fields that should change based "
        "on the instruction — do not repeat unchanged fields. Respond as JSON with key "
        "'updates': an object containing only the changed field names (from: complaint_source, "
        "customer_name, product_name, product_strength, batch_number, affected_quantity, "
        "manufacturing_date, expiry_date, manufacturing_site, material_type, complaint_date, "
        "complaint_description, complaint_category) mapped to their new values."
    )
    current_values = {f: existing.get(f) for f in FORM_FIELDS}
    user_prompt = f"CURRENT VALUES:\n{current_values}\n\nINSTRUCTION: {state.get('user_message')}"

    result = call_llm_json(system_prompt, user_prompt)
    updates = result.get("updates", {}) or {}
    updates = {k: v for k, v in updates.items() if k in FORM_FIELDS and v is not None}

    # Merge: start from the existing record, apply only what changed.
    merged = {f: existing.get(f) for f in FORM_FIELDS}
    merged.update(updates)
    merged["changed_fields"] = list(updates.keys())
    return merged


# ---------------------------------------------------------------------------
# Shared risk-assessment pipeline — runs after every tool so the form and
# the AI Risk Assessment panel always reflect the complaint's current state.
# ---------------------------------------------------------------------------
def completeness_check_node(state: CopilotState) -> dict:
    """Deterministic/local: flag which required fields are still empty."""
    missing = [f for f in REQUIRED_FIELDS if not state.get(f)]
    score = round(100 * (len(REQUIRED_FIELDS) - len(missing)) / len(REQUIRED_FIELDS), 1)
    return {"missing_fields": missing, "completeness_score": score}


def risk_classification_node(state: CopilotState) -> dict:
    system_prompt = (
        "You are a pharmaceutical QMS risk assessment copilot. Classify the complaint's risk "
        "level using standard GMP complaint-handling severity tiers:\n"
        "- Critical: potential patient safety impact (contamination, wrong drug/strength, "
        "life-threatening adverse event, sterility failure).\n"
        "- Major: significant quality defect without immediate safety impact (dosage form "
        "defect, packaging breach affecting product integrity, potency/stability concern).\n"
        "- Minor: cosmetic, labeling typo, delivery/logistics issue with no quality impact.\n"
        "If there isn't enough information yet to classify, respond with risk_level "
        "'Unclassified'. Respond as JSON with keys: risk_level (Critical|Major|Minor|"
        "Unclassified) and risk_justification (1-2 sentences)."
    )
    user_prompt = (
        f"Category: {state.get('complaint_category')}\n"
        f"Description: {state.get('complaint_description')}\n"
        f"Product: {state.get('product_name')} {state.get('product_strength') or ''}\n"
        f"Affected quantity: {state.get('affected_quantity')}"
    )
    result = call_llm_json(system_prompt, user_prompt)
    return {
        "risk_level": result.get("risk_level", "Unclassified"),
        "risk_justification": result.get("risk_justification", ""),
    }


def root_cause_node(state: CopilotState) -> dict:
    if not state.get("complaint_description"):
        return {"root_cause_suggestions": []}
    system_prompt = (
        "You are a pharmaceutical manufacturing quality investigator. Given a customer "
        "complaint about an API or FDF product, suggest 2-4 plausible root-cause hypotheses "
        "an investigator should check first (e.g. raw material variability, equipment "
        "calibration drift, storage/transport temperature excursion, operator error, "
        "packaging line contamination). Respond as JSON with key root_cause_suggestions: a "
        "list of short strings."
    )
    result = call_llm_json(system_prompt, state.get("complaint_description", ""))
    return {"root_cause_suggestions": result.get("root_cause_suggestions", [])}


def capa_node(state: CopilotState) -> dict:
    if not state.get("complaint_description"):
        return {"capa_recommendations": []}
    system_prompt = (
        "You are a pharmaceutical QMS CAPA (Corrective and Preventive Action) advisor. Given a "
        "complaint, its risk level, and likely root causes, propose 2-4 concrete next steps "
        "(mix of immediate corrective actions and longer-term preventive actions, e.g. 'Open a "
        "QA investigation', 'Quarantine remaining batch stock'). Respond as JSON with key "
        "capa_recommendations: a list of short, actionable strings."
    )
    user_prompt = (
        f"Complaint: {state.get('complaint_description')}\n"
        f"Risk level: {state.get('risk_level')}\n"
        f"Suspected root causes: {state.get('root_cause_suggestions')}"
    )
    result = call_llm_json(system_prompt, user_prompt)
    return {"capa_recommendations": result.get("capa_recommendations", [])}


def duplicate_detection_node(state: CopilotState) -> dict:
    existing = state.get("existing_complaints_for_dup_check") or []
    if not existing or not state.get("complaint_description"):
        return {"is_possible_duplicate": False, "duplicate_of": None, "duplicate_reason": None}

    system_prompt = (
        "You compare a complaint against a list of OTHER existing complaints (same company) "
        "to detect likely duplicates — the same underlying issue (same product + same defect "
        "type), even if worded differently. Respond as JSON with keys: is_duplicate (bool), "
        "duplicate_id (the id string of the matching complaint, or null), reason (1 sentence, "
        "or null)."
    )
    user_prompt = (
        f"THIS complaint:\nProduct: {state.get('product_name')}\n"
        f"Description: {state.get('complaint_description')}\n\n"
        f"OTHER complaints:\n{existing}"
    )
    result = call_llm_json(system_prompt, user_prompt)
    return {
        "is_possible_duplicate": bool(result.get("is_duplicate", False)),
        "duplicate_of": result.get("duplicate_id"),
        "duplicate_reason": result.get("reason"),
    }


def summarize_node(state: CopilotState) -> dict:
    if not state.get("complaint_description"):
        return {"ai_summary": ""}
    system_prompt = (
        "Summarize this pharmaceutical customer complaint in 2-3 sentences for a Quality "
        "Assurance reviewer: what happened, the product/batch involved, and why it matters. "
        "Respond as JSON with key ai_summary: a string."
    )
    user_prompt = f"Complaint: {state.get('complaint_description')}\nRisk: {state.get('risk_level')} — {state.get('risk_justification')}"
    result = call_llm_json(system_prompt, user_prompt)
    return {"ai_summary": result.get("ai_summary", "")}


def generate_reply_node(state: CopilotState) -> dict:
    """Craft the natural-language chat bubble shown back to the user.

    Deterministic/local (not an LLM call): the exact fields that changed are
    already known precisely (from `changed_fields`), so templating a
    confirmation is both cheaper and more accurate than asking an LLM to
    describe its own diff.
    """
    mode = state.get("mode")
    changed = state.get("changed_fields") or []

    if mode == "edit":
        if not changed:
            reply = "I didn't find anything to update from that — could you rephrase which field to change?"
        else:
            pretty = ", ".join(f'{f.replace("_", " ").title()} to "{state.get(f)}"' for f in changed)
            reply = f"Got it. I've updated {pretty} in the form."
    elif mode == "extract_document":
        product = state.get("product_name") or "the product"
        reply = (
            f"Document analysis complete. I've extracted the complaint details for {product} "
            f"and classified it as {state.get('risk_level', 'Unclassified')} risk. "
            f"Form populated on the left."
        )
    else:  # log
        product = state.get("product_name") or "this complaint"
        reply = (
            f"Logged. I've filled in what {product} complaint details were provided and "
            f"classified it as {state.get('risk_level', 'Unclassified')} risk"
            + (f" — {state.get('risk_justification')}" if state.get("risk_justification") else "")
            + f". Completeness is at {state.get('completeness_score', 0)}%"
            + (f"; still missing: {', '.join(state.get('missing_fields'))}." if state.get("missing_fields") else ".")
        )

    if state.get("is_possible_duplicate"):
        reply += f" ⚠ Note: this looks like a possible duplicate — {state.get('duplicate_reason', '')}"

    return {"assistant_reply": reply}
