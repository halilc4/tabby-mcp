"""MCP tool definitions for Tabby."""

import json
import logging
from typing import Any

from mcp.server import Server
from mcp.types import Tool, TextContent, ImageContent

from .cdp import get_connection

logger = logging.getLogger(__name__)


def _validate_target(arguments: dict[str, Any]) -> int | str:
    """Validate and return target argument."""
    target = arguments.get("target")
    if target is None:
        raise ValueError("target is required")
    if not isinstance(target, (int, str)):
        raise ValueError(f"target must be int or str, got {type(target).__name__}")
    return target


def _validate_screenshot_args(arguments: dict[str, Any]) -> tuple[str, int]:
    """Validate screenshot format and quality, return (format, quality)."""
    fmt = arguments.get("format", "jpeg")
    if fmt not in ("png", "jpeg"):
        raise ValueError(f"format must be 'png' or 'jpeg', got '{fmt}'")
    quality = arguments.get("quality", 80)
    if not isinstance(quality, int) or not 0 <= quality <= 100:
        raise ValueError(f"quality must be int 0-100, got {quality}")
    return fmt, quality


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
                            "default": "jpeg",
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
    async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent | ImageContent]:
        logger.debug("Tool call: %s, args: %s", name, arguments)
        conn = get_connection()

        try:
            if name == "list_targets":
                targets = conn.list_targets()
                return [TextContent(type="text", text=json.dumps(targets, indent=2))]

            elif name == "execute_js":
                target = _validate_target(arguments)
                code = arguments.get("code", "")
                if not code:
                    raise ValueError("code is required and must be non-empty")
                wrap = arguments.get("wrap", True)
                result = conn.execute_js(code, target, wrap=wrap)
                return [TextContent(type="text", text=json.dumps(result, default=str))]

            elif name == "query":
                target = _validate_target(arguments)
                selector = arguments.get("selector", "")
                if not selector:
                    raise ValueError("selector is required and must be non-empty")
                include_children = arguments.get("include_children", False)
                include_text = arguments.get("include_text", True)
                skip_wait = arguments.get("skip_wait", False)
                if not skip_wait:
                    conn.wait_for_angular(target)
                    conn.wait_for(selector, target, timeout=2.0)
                elements = conn.query(selector, target, include_children, include_text)
                return [TextContent(type="text", text=json.dumps(elements, indent=2))]

            elif name == "screenshot":
                target = _validate_target(arguments)
                fmt, quality = _validate_screenshot_args(arguments)
                data = conn.screenshot(target, fmt, quality)
                mime_type = "image/png" if fmt == "png" else "image/jpeg"
                return [ImageContent(type="image", data=data, mimeType=mime_type)]

            return [TextContent(type="text", text=f"Unknown tool: {name}")]

        except Exception as e:
            logger.exception("%s failed", name)
            return [TextContent(type="text", text=f"Error: {e}")]
