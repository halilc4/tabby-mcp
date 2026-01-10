# tabby-mcp

MCP server za kontrolu Tabby terminala preko Chrome DevTools Protocol (CDP).

## Arhitektura

```
server.py  ->  tools.py  ->  cdp.py  ->  Tabby (CDP port 9222)
```

- `server.py` - MCP server entry point, stdio transport
- `tools.py` - MCP tool definicije (execute_js, query)
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
| `execute_js` | Execute JS u Tabby kontekstu |
| `query` | Query DOM elemente po CSS selektoru |

## CDP Helper metode (cdp.py)

- `execute_js(expression)` - Execute JS, vrati rezultat
- `query(selector)` - Query elementi, vrati info (tagName, id, className, text)
- `click(selector, index)` - Klikni element
- `get_text(selector)` - Vrati textContent
- `wait_for(selector, timeout)` - Cekaj da element postoji

## Konvencije

- Python 3.10+
- Type hints obavezni
- Async za server, sync za CDP metode
- Error handling: raise exceptions, ne vracaj None za greske
