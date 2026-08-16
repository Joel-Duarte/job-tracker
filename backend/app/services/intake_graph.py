import logging
from typing import Literal

from langgraph.graph import END, START, StateGraph

from app.schemas.graph_state import JobTrackerState
from app.services.graph_nodes import (
    db_commit_node,
    extraction_node,
    fuzzy_match_node,
    normalize_and_dedupe_node,
    scrape_enrich_node,
    staging_node,
    summarize_embed_node,
)

logger = logging.getLogger(__name__)


def route_after_dedupe(state: JobTrackerState) -> Literal["extraction", "__end__"]:
    if state.get("is_duplicate"):
        return END
    return "extraction"


def route_after_extraction(
    state: JobTrackerState,
) -> Literal["fuzzy_match", "db_commit"]:
    if not state.get("is_application"):
        return "db_commit"
    return "fuzzy_match"


def route_after_fuzzy_match(
    state: JobTrackerState,
) -> Literal["staging", "scrape_enrich", "db_commit"]:
    if state.get("route") == "staging":
        return "staging"
    if state.get("job_url"):
        return "scrape_enrich"
    return "db_commit"


def route_after_commit(state: JobTrackerState) -> Literal["summarize_embed", "__end__"]:
    if state.get("application_id"):
        return "summarize_embed"
    return END


def build_intake_graph():
    builder = StateGraph(JobTrackerState)

    builder.add_node("normalize_and_dedupe", normalize_and_dedupe_node)
    builder.add_node("extraction", extraction_node)
    builder.add_node("fuzzy_match", fuzzy_match_node)
    builder.add_node("staging", staging_node)
    builder.add_node("scrape_enrich", scrape_enrich_node)
    builder.add_node("db_commit", db_commit_node)
    builder.add_node("summarize_embed", summarize_embed_node)

    builder.add_edge(START, "normalize_and_dedupe")
    builder.add_conditional_edges("normalize_and_dedupe", route_after_dedupe)
    builder.add_conditional_edges("extraction", route_after_extraction)
    builder.add_conditional_edges("fuzzy_match", route_after_fuzzy_match)
    builder.add_edge("staging", END)
    builder.add_edge("scrape_enrich", "db_commit")
    builder.add_conditional_edges("db_commit", route_after_commit)
    builder.add_edge("summarize_embed", END)

    return builder.compile()


intake_graph = build_intake_graph()
