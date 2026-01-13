# Changelog

## [0.1.0] - 2026-01-13

Initial PyPI release.

### Features

- `list_targets` - List CDP targets (tabs) with index, title, url, ws_url
- `execute_js` - Execute JavaScript in Tabby context (async IIFE wrap by default)
- `query` - Query DOM elements with CSS selector (auto-waits for Angular)
- `screenshot` - Capture Tabby window screenshot

### Technical

- Python 3.10+ support
- MCP server with stdio transport
- CDP communication via pychrome library
