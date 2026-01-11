"""Tabby MCP Server - Entry point."""

import asyncio
import logging
import sys

from mcp.server import Server
from mcp.server.stdio import stdio_server

from .tools import register_tools


def setup_logging() -> None:
    """Configure logging to stderr."""
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        stream=sys.stderr,
    )


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
    setup_logging()
    try:
        asyncio.run(run_server())
    except KeyboardInterrupt:
        pass
    except Exception as e:
        logging.exception("Server crashed")
        sys.exit(1)


if __name__ == "__main__":
    main()
