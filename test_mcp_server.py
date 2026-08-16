import sys
sys.path.insert(0, "./backend")
from app.services.mcp_server import mcp_server
print(mcp_server.name)
