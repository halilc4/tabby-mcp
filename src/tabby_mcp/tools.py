"""MCP tool definitions for Tabby."""

import json

from mcp.server import Server
from mcp.types import Tool, TextContent

from .cdp import get_connection


def register_tools(server: Server) -> None:
    """Register all MCP tools with the server."""

    @server.list_tools()
    async def list_tools() -> list[Tool]:
        return [
            Tool(
                name="execute_js",
                description="Execute JavaScript code in Tabby terminal context and return the result",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "code": {
                            "type": "string",
                            "description": "JavaScript code to execute",
                        }
                    },
                    "required": ["code"],
                },
            ),
            Tool(
                name="query",
                description="Query DOM elements by CSS selector, returns list of elements with info (tagName, id, className, textContent)",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "selector": {
                            "type": "string",
                            "description": "CSS selector to query",
                        }
                    },
                    "required": ["selector"],
                },
            ),
        ]

    @server.call_tool()
    async def call_tool(name: str, arguments: dict) -> list[TextContent]:
        conn = get_connection()

        if name == "execute_js":
            code = arguments.get("code", "")
            try:
                result = conn.execute_js(code)
                return [TextContent(type="text", text=json.dumps(result, default=str))]
            except Exception as e:
                return [TextContent(type="text", text=f"Error: {e}")]

        elif name == "query":
            selector = arguments.get("selector", "")
            try:
                elements = conn.query(selector)
                return [TextContent(type="text", text=json.dumps(elements, indent=2))]
            except Exception as e:
                return [TextContent(type="text", text=f"Error: {e}")]

        return [TextContent(type="text", text=f"Unknown tool: {name}")]
