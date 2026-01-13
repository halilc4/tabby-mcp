# tabby-mcp

MCP server for controlling Tabby terminal via Chrome DevTools Protocol (CDP).

## Architecture

```
server.py  ->  tools.py  ->  cdp.py  ->  Tabby (CDP port 9222)
```

- `server.py` - MCP server entry point, stdio transport
- `tools.py` - MCP tool definitions (execute_js, query, screenshot)
- `cdp.py` - TabbyConnection class, CDP communication

## Development

```bash
# Install dependencies
uv sync

# Run server
uv run tabby-mcp

# Tabby must be started with CDP debugging:
# tabby.exe --remote-debugging-port=9222
```

## MCP Tools

| Tool | Description |
|------|-------------|
| `list_targets` | List CDP targets (tabs) with index, title, url, ws_url |
| `execute_js` | Execute JS in Tabby context (async IIFE wrap by default) |
| `query` | Query DOM elements (auto-waits for Angular) |
| `screenshot` | Capture screenshot of Tabby window |

### execute_js parameters

- `target` - Tab index (0=first, -1=last) or ws_url
- `code` - JavaScript code. Use `return` to return values
- `wrap` - Wrap in async IIFE (default: true). Fresh scope + await support. Set to false for raw execution (global functions, etc.)

### query parameters

- `selector` - CSS selector
- `include_children` - Include children preview (default: false)
- `include_text` - Include textContent (default: true)
- `skip_wait` - Skip Angular/element wait (default: false)

Query automatically waits for Angular Zone.js stable and element existence.
Use `skip_wait=true` only when you know the element already exists.

## CDP Helper methods (cdp.py)

- `execute_js(expression, target, wrap=True)` - Execute JS, return result. wrap=True for IIFE+async
- `list_targets()` - List tabs with index, title, url, ws_url
- `query(selector)` - Query elements, return info (tagName, id, className, text)
- `query_with_retry(selector, max_retries, delay)` - Query with retry for dynamic elements
- `click(selector, index)` - Click element
- `get_text(selector)` - Return textContent
- `wait_for(selector, timeout, visible)` - Wait for element to exist (internal)
- `wait_for_angular(timeout)` - Wait for Angular Zone.js stable (internal)
- `screenshot(format, quality)` - Capture screenshot, return base64

## Conventions

- Python 3.10+
- Type hints required
- Async for server, sync for CDP methods
- Error handling: raise exceptions, don't return None for errors
