"""MCP tool definitions for Tabby."""

import json

from mcp.server import Server
from mcp.types import Tool, TextContent, ImageContent

from .cdp import get_connection


TARGET_SCHEMA = {
    "type": ["integer", "string"],
    "description": "Target tab: index (0=first, -1=last) or WebSocket URL from list_targets",
}


def register_tools(server: Server) -> None:
    """Register all MCP tools with the server."""

    @server.list_tools()
    async def list_tools() -> list[Tool]:
        return [
            Tool(
                name="list_targets",
                description="List available CDP targets (tabs) with their index, URL, and WebSocket URL",
                inputSchema={
                    "type": "object",
                    "properties": {},
                    "required": [],
                },
            ),
            Tool(
                name="execute_js",
                description="Execute JavaScript code in Tabby terminal context and return the result",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "target": TARGET_SCHEMA,
                        "code": {
                            "type": "string",
                            "description": "JavaScript code to execute",
                        },
                    },
                    "required": ["target", "code"],
                },
            ),
            Tool(
                name="query",
                description="Query DOM elements by CSS selector, returns list of elements with info (tagName, id, className, textContent)",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "target": TARGET_SCHEMA,
                        "selector": {
                            "type": "string",
                            "description": "CSS selector to query",
                        },
                    },
                    "required": ["target", "selector"],
                },
            ),
            Tool(
                name="screenshot",
                description="Capture screenshot of Tabby terminal window",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "target": TARGET_SCHEMA,
                        "format": {
                            "type": "string",
                            "enum": ["png", "jpeg"],
                            "default": "png",
                            "description": "Image format",
                        },
                        "quality": {
                            "type": "integer",
                            "minimum": 0,
                            "maximum": 100,
                            "default": 80,
                            "description": "JPEG quality (ignored for PNG)",
                        },
                    },
                    "required": ["target"],
                },
            ),
        ]

    @server.call_tool()
    async def call_tool(name: str, arguments: dict) -> list[TextContent | ImageContent]:
        conn = get_connection()

        if name == "list_targets":
            try:
                targets = conn.list_targets()
                return [TextContent(type="text", text=json.dumps(targets, indent=2))]
            except Exception as e:
                return [TextContent(type="text", text=f"Error: {e}")]

        elif name == "execute_js":
            target = arguments.get("target")
            code = arguments.get("code", "")
            try:
                result = conn.execute_js(code, target)
                return [TextContent(type="text", text=json.dumps(result, default=str))]
            except Exception as e:
                return [TextContent(type="text", text=f"Error: {e}")]

        elif name == "query":
            target = arguments.get("target")
            selector = arguments.get("selector", "")
            try:
                elements = conn.query(selector, target)
                return [TextContent(type="text", text=json.dumps(elements, indent=2))]
            except Exception as e:
                return [TextContent(type="text", text=f"Error: {e}")]

        elif name == "screenshot":
            target = arguments.get("target")
            fmt = arguments.get("format", "png")
            quality = arguments.get("quality", 80)
            try:
                data = conn.screenshot(target, fmt, quality)
                mime_type = "image/png" if fmt == "png" else "image/jpeg"
                return [ImageContent(type="image", data=data, mimeType=mime_type)]
            except Exception as e:
                return [TextContent(type="text", text=f"Error: {e}")]

        return [TextContent(type="text", text=f"Unknown tool: {name}")]
