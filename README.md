# tabby-mcp

A lightweight MCP (Model Context Protocol) server that enables control of the [Tabby](https://tabby.sh/) terminal via Chrome DevTools Protocol (CDP).

## Features

- **list_targets** - List CDP targets (tabs) with index, title, url, ws_url
- **execute_js** - Execute JavaScript code in Tabby's Electron context
- **query** - Query DOM elements by CSS selector (auto-waits for Angular)
- **screenshot** - Capture Tabby window screenshot

## About this project

This MCP server was built to automate development and testing of [TabbySpaces](https://github.com/halilc4/tabbyspaces).

TabbySpaces was written 100% by Claude Code - Igor didn't look at the Angular code once. But for this Python project, he has MCP experience and actually reviewed the code.

Here's the fun part: Claude Code (running inside TabbySpaces) served as the tester for this project. The AI that built the plugin now uses this MCP server to test it. Full circle.

## Requirements

- Python 3.10+
- [uv](https://docs.astral.sh/uv/) package manager
- Tabby terminal with CDP debugging enabled

## Installation

### From PyPI (recommended)

```bash
pip install tabby-mcp
```

Or with uv:

```bash
uv pip install tabby-mcp
```

### From source

```bash
git clone https://github.com/halilc4/tabby-mcp.git
cd tabby-mcp
uv sync
```

## Setup

### 1. Launch Tabby with CDP debugging

```bash
tabby.exe --remote-debugging-port=9222
```

### 2. Configure Claude Code

Add to your Claude Code MCP settings (`~/.claude/claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "tabby": {
      "command": "uv",
      "args": ["--directory", "/path/to/tabby-mcp", "run", "tabby-mcp"]
    }
  }
}
```

## Usage

Once configured, Claude Code can interact with Tabby through MCP tools:

```
# Execute JavaScript
execute_js({ "code": "document.title" })

# Query DOM elements
query({ "selector": ".tab-bar button" })
```

## Architecture

```
server.py  ->  tools.py  ->  cdp.py  ->  Tabby (CDP port 9222)
```

| Module | Purpose |
|--------|---------|
| `server.py` | MCP server entry point with stdio transport |
| `tools.py` | MCP tool definitions and handlers |
| `cdp.py` | CDP connection management via pychrome |

## License

MIT
