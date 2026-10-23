"""
LangGraph workflow definition for the Sentinel.

Graph shape:

                              START
                                |
                  (conditional: route_by_mode)
                    /           |            \\
                   v            v             v
         extract_from_    apply_edit_   extract_from_
         message_node     node          document_node
         (Log Complaint)  (Edit         (Document
                           Complaint)    Extraction)
                    \\           |            /
                     \\          |           /
                      v          v          v
                    completeness_check_node
                                |
                    risk_classification_node
                                |
                     root_cause_recommendation
                                |
                      capa_recommendation
                                |
                     duplicate_detection
                                |
                          summarize
                                |
                        generate_reply
                                |
                               END

Routing between the three tools is deterministic, based on the shape of the
incoming request (handled in `route_by_mode` / set by the API layer):
  - a file was attached                     -> "extract_document"
  - no file, but an existing complaint id    -> "edit"
  - no file, no existing complaint           -> "log"

This keeps tool selection 100% reliable for a live demo rather than
depending on a small model's function-calling accuracy — the actual
reasoning (what to extract, what to change, how to assess risk) is still
fully delegated to the LLM inside each tool/node. Swapping this for
LLM-driven tool selection (Groq supports OpenAI-style tool calling on
llama-3.3-70b-versatile) would be a natural next step for a production
version with more model headroom.
"""
from langgraph.graph import StateGraph, END

from app.agents.nodes import (
    CopilotState,
    extract_from_message_node,
    extract_from_document_node,
    apply_edit_node,
    completeness_check_node,
    risk_classification_node,
    root_cause_node,
    capa_node,
    duplicate_detection_node,
    summarize_node,
    generate_reply_node,
)


def _route_by_mode(state: CopilotState) -> str:
    """Conditional-edge function: dispatch to the right tool based on `mode`."""
    return state.get("mode", "log")


def build_copilot_graph():
    graph = StateGraph(CopilotState)

    # --- the three tools ---
    graph.add_node("log_complaint", extract_from_message_node)
    graph.add_node("edit_complaint", apply_edit_node)
    graph.add_node("document_extraction", extract_from_document_node)

    # --- shared risk-assessment pipeline ---
    graph.add_node("completeness_check", completeness_check_node)
    graph.add_node("risk_classification", risk_classification_node)
    graph.add_node("root_cause_recommendation", root_cause_node)
    graph.add_node("capa_recommendation", capa_node)
    graph.add_node("duplicate_detection", duplicate_detection_node)
    graph.add_node("summarize", summarize_node)
    graph.add_node("generate_reply", generate_reply_node)

    graph.set_conditional_entry_point(
        _route_by_mode,
        {
            "log": "log_complaint",
            "edit": "edit_complaint",
            "extract_document": "document_extraction",
        },
    )

    # all three tools funnel into the same shared pipeline
    for tool_node in ("log_complaint", "edit_complaint", "document_extraction"):
        graph.add_edge(tool_node, "completeness_check")

    graph.add_edge("completeness_check", "risk_classification")
    graph.add_edge("risk_classification", "root_cause_recommendation")
    graph.add_edge("root_cause_recommendation", "capa_recommendation")
    graph.add_edge("capa_recommendation", "duplicate_detection")
    graph.add_edge("duplicate_detection", "summarize")
    graph.add_edge("summarize", "generate_reply")
    graph.add_edge("generate_reply", END)

    return graph.compile()


# Compiled once at import time and reused across requests.
copilot_graph = build_copilot_graph()
