import logging
from mcp.server.mcpserver import MCPServer
import mcp.types as types

logger = logging.getLogger(__name__)

mcp_server = MCPServer("backend-mcp-server")

@mcp_server.tool()
async def trigger_workflow(workflow_name: str, input_data: dict) -> list[types.TextContent]:
    """Trigger a backend workflow"""
    return [types.TextContent(type="text", text=f"Triggered {workflow_name}")]

@mcp_server.tool()
async def run_intake_graph(url: str = "", raw_text: str = "", email_id: str = "", email_body: str = "") -> list[types.TextContent]:
    """Run the intake graph workflow to process a job or application. Returns the output graph state."""
    from app.core.mcp_context import mcp_session_var
    from app.core.database import SessionLocal
    from app.services.intake_graph import build_intake_graph

    mcp_session_var.set(mcp_server.request_context.session)
    graph = build_intake_graph()
    initial_state = {
        "source_url": url,
        "raw_text": raw_text,
        "source_email_id": email_id,
        "email_body": email_body
    }
    try:
        async with SessionLocal() as db:
            config = {"configurable": {"db": db}}
            result = await graph.ainvoke(initial_state, config=config)
        return [types.TextContent(type="text", text=f"Intake graph completed. State: {str(result)}")]
    except Exception as e:
        return [types.TextContent(type="text", text=f"Error: {e}")]

@mcp_server.tool()
async def run_interview_guide(job_id: str) -> list[types.TextContent]:
    """Generate an interview guide for a job ID."""
    from app.core.mcp_context import mcp_session_var
    from app.core.database import SessionLocal
    from app.services.interview_guide_graph import build_interview_guide_graph

    mcp_session_var.set(mcp_server.request_context.session)
    graph = build_interview_guide_graph()
    initial_state = {"job_id": job_id}
    try:
        async with SessionLocal() as db:
            config = {"configurable": {"db": db}}
            result = await graph.ainvoke(initial_state, config=config)
        return [types.TextContent(type="text", text=f"Interview guide graph completed. State: {str(result)}")]
    except Exception as e:
        return [types.TextContent(type="text", text=f"Error: {e}")]

@mcp_server.tool()
async def search_db(query: str) -> list[types.TextContent]:
    """Search the local database vectors using text search."""
    from app.core.mcp_context import mcp_session_var
    from app.core.database import SessionLocal
    from sqlalchemy import text

    mcp_session_var.set(mcp_server.request_context.session)
    try:
        async with SessionLocal() as db:
            stmt = text("SELECT id, job_title, company_name FROM tracked_jobs WHERE job_title ILIKE :q OR company_name ILIKE :q LIMIT 5")
            res = await db.execute(stmt, {"q": f"%{query}%"})
            rows = res.fetchall()
            results = [{"id": r.id, "job_title": r.job_title, "company_name": r.company_name} for r in rows]
        return [types.TextContent(type="text", text=f"Search results for '{query}': {str(results)}")]
    except Exception as e:
        return [types.TextContent(type="text", text=f"Error: {e}")]
