"""Tabby MCP Server - Entry point."""

import asyncio
import sys

from mcp.server import Server
from mcp.server.stdio import stdio_server

from .tools import register_tools


def create_server() -> Server:
    """Create and configure the MCP server."""
    server = Server("tabby-mcp")
    register_tools(server)
    return server


async def run_server() -> None:
    """Run the MCP server with stdio transport."""
    server = create_server()

    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options(),
        )


def main() -> None:
    """Main entry point."""
    try:
        asyncio.run(run_server())
    except KeyboardInterrupt:
        pass
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
