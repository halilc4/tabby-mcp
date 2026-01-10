# Contributing to tabby-mcp

Thanks for your interest in contributing!

## Development Setup

### Prerequisites

- Python 3.10+
- [uv](https://docs.astral.sh/uv/) package manager
- [Tabby](https://tabby.sh/) terminal

### Setup

```bash
git clone https://github.com/halilc4/tabby-mcp.git
cd tabby-mcp
uv sync
```

### Running Locally

1. Start Tabby with CDP debugging enabled:
   ```bash
   tabby.exe --remote-debugging-port=9222
   ```

2. Run the MCP server:
   ```bash
   uv run tabby-mcp
   ```

## Code Style

- Use type hints for all function parameters and return values
- Follow existing patterns in the codebase
- Keep functions focused and single-purpose
- Handle errors explicitly with exceptions

## Pull Request Process

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/my-feature`)
3. Make your changes
4. Test locally with Tabby
5. Commit with clear messages
6. Push and open a Pull Request

## Adding New MCP Tools

To add a new tool:

1. Add the tool definition in `src/tabby_mcp/tools.py` under `list_tools()`
2. Add the handler in `call_tool()`
3. If needed, add helper methods in `src/tabby_mcp/cdp.py`

## Questions?

Open an issue if you have questions or need help.
