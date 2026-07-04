"""Synchronous bridge to the local MCP server (mcp_server.py).

MCP's client is async and talks to the server over stdio. The rest of the app (Streamlit + the tool
loop) is synchronous, so we wrap each interaction in asyncio.run(): spawn the server as a subprocess,
do the MCP handshake, list or call tools, tear down. Stateless calculators make per-call connections fine.
"""

import sys
import asyncio
from pathlib import Path
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

_SERVER_PATH = str(Path(__file__).parent / "mcp_server.py")


def _params() -> StdioServerParameters:
    return StdioServerParameters(command=sys.executable, args=[_SERVER_PATH])


async def _alist_tools() -> list[dict]:
    async with stdio_client(_params()) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            resp = await session.list_tools()
            return [
                {"name": t.name, "description": t.description or "", "input_schema": t.inputSchema}
                for t in resp.tools
            ]


async def _acall_tool(name: str, args: dict) -> str:
    async with stdio_client(_params()) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool(name, args)
            texts = [c.text for c in result.content if getattr(c, "type", None) == "text"]
            return "\n".join(texts) or "(no output)"


def list_mcp_tools() -> list[dict]:
    """Discover the tools the MCP server exposes (Anthropic tool-schema shape). [] on failure."""
    try:
        return asyncio.run(_alist_tools())
    except Exception as e:  # keep the app working even if MCP is unavailable
        print(f"[mcp_bridge] list_tools failed: {e}", file=sys.stderr)
        return []


def call_mcp_tool(name: str, args: dict) -> str:
    """Call one MCP tool and return its text result."""
    try:
        return asyncio.run(_acall_tool(name, args))
    except Exception as e:
        return f"(MCP tool error: {e})"
