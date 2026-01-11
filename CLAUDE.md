# tabby-mcp

MCP server za kontrolu Tabby terminala preko Chrome DevTools Protocol (CDP).

## Arhitektura

```
server.py  ->  tools.py  ->  cdp.py  ->  Tabby (CDP port 9222)
```

- `server.py` - MCP server entry point, stdio transport
- `tools.py` - MCP tool definicije (execute_js, query, screenshot)
- `cdp.py` - TabbyConnection klasa, CDP komunikacija

## Razvoj

```bash
# Install dependencies
uv sync

# Run server
uv run tabby-mcp

# Tabby mora biti pokrenut sa CDP debugging:
# tabby.exe --remote-debugging-port=9222
```

## MCP Tools

| Tool | Opis |
|------|------|
| `list_targets` | Lista CDP targeta (tabova) sa index, title, url, ws_url |
| `execute_js` | Execute JS u Tabby kontekstu (async IIFE wrap po defaultu) |
| `query` | Query DOM elemente (automatski ceka Angular) |
| `screenshot` | Capture screenshot Tabby prozora |

### execute_js parametri

- `target` - Tab index (0=first, -1=last) ili ws_url
- `code` - JavaScript kod. Koristi `return` za vracanje vrednosti
- `wrap` - Wrap u async IIFE (default: true). Fresh scope + await podrska. Postavi na false za raw execution (globalne funkcije, etc.)

### query parametri

- `selector` - CSS selector
- `include_children` - Ukljuci preview dece (default: false)
- `include_text` - Ukljuci textContent (default: true)
- `skip_wait` - Preskoci Angular/element wait (default: false)

Query automatski ceka Angular Zone.js stable i element da postoji.
Koristi `skip_wait=true` samo kad znas da element vec postoji.

## CDP Helper metode (cdp.py)

- `execute_js(expression, target, wrap=True)` - Execute JS, vrati rezultat. wrap=True za IIFE+async
- `list_targets()` - Lista tabova sa index, title, url, ws_url
- `query(selector)` - Query elementi, vrati info (tagName, id, className, text)
- `query_with_retry(selector, max_retries, delay)` - Query sa retry za dinamicke elemente
- `click(selector, index)` - Klikni element
- `get_text(selector)` - Vrati textContent
- `wait_for(selector, timeout, visible)` - Cekaj da element postoji (interno)
- `wait_for_angular(timeout)` - Cekaj Angular Zone.js stable (interno)
- `screenshot(format, quality)` - Capture screenshot, vrati base64

## Konvencije

- Python 3.10+
- Type hints obavezni
- Async za server, sync za CDP metode
- Error handling: raise exceptions, ne vracaj None za greske
