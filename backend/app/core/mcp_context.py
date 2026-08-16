import contextvars

# Global context var to hold the active MCP server session, if any
mcp_session_var = contextvars.ContextVar("mcp_session", default=None)
