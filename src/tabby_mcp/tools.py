"""MCP tool definitions for Tabby."""

import json
import logging

from mcp.server import Server
from mcp.types import Tool, TextContent, ImageContent

from .cdp import get_connection

logger = logging.getLogger(__name__)


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
                description="Execute JavaScript code in Tabby terminal context and return the result. Code is wrapped in async IIFE by default for fresh scope and await support.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "target": TARGET_SCHEMA,
                        "code": {
                            "type": "string",
                            "description": "JavaScript code to execute. Use 'return' to return values.",
                        },
                        "wrap": {
                            "type": "boolean",
                            "default": True,
                            "description": "Wrap code in async IIFE for fresh scope + await support. Set to false for raw execution (e.g., defining globals).",
                        },
                    },
                    "required": ["target", "code"],
                },
            ),
            Tool(
                name="query",
                description="Query DOM elements by CSS selector. Automatically waits for Angular and element to exist.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "target": TARGET_SCHEMA,
                        "selector": {
                            "type": "string",
                            "description": "CSS selector to query",
                        },
                        "include_children": {
                            "type": "boolean",
                            "default": False,
                            "description": "Include children preview (first 10, with tagName, id, className)",
                        },
                        "include_text": {
                            "type": "boolean",
                            "default": True,
                            "description": "Include textContent (truncated to 200 chars)",
                        },
                        "skip_wait": {
                            "type": "boolean",
                            "default": False,
                            "description": "Skip Angular/element wait (use when element definitely exists)",
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
        logger.info("Tool call: %s, args: %s", name, arguments)
        conn = get_connection()

        if name == "list_targets":
            try:
                targets = conn.list_targets()
                return [TextContent(type="text", text=json.dumps(targets, indent=2))]
            except Exception as e:
                logger.exception("list_targets failed")
                return [TextContent(type="text", text=f"Error: {e}")]

        elif name == "execute_js":
            target = arguments.get("target")
            code = arguments.get("code", "")
            wrap = arguments.get("wrap", True)
            try:
                result = conn.execute_js(code, target, wrap=wrap)
                return [TextContent(type="text", text=json.dumps(result, default=str))]
            except Exception as e:
                logger.exception("execute_js failed")
                return [TextContent(type="text", text=f"Error: {e}")]

        elif name == "query":
            target = arguments.get("target")
            selector = arguments.get("selector", "")
            include_children = arguments.get("include_children", False)
            include_text = arguments.get("include_text", True)
            skip_wait = arguments.get("skip_wait", False)
            try:
                if not skip_wait:
                    conn.wait_for_angular(target)
                    conn.wait_for(selector, target, timeout=2.0)
                elements = conn.query(selector, target, include_children, include_text)
                return [TextContent(type="text", text=json.dumps(elements, indent=2))]
            except Exception as e:
                logger.exception("query failed")
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
                logger.exception("screenshot failed")
                return [TextContent(type="text", text=f"Error: {e}")]

        return [TextContent(type="text", text=f"Unknown tool: {name}")]
