"""CDP connection and helper methods for Tabby."""

import time
import urllib.request
import json as json_module
from typing import Any

import pychrome


class TabbyConnection:
    """Manages CDP connection to Tabby terminal."""

    def __init__(self, port: int = 9222):
        self.port = port
        self.browser: pychrome.Browser | None = None
        self._tabs: dict[str, pychrome.Tab] = {}  # ws_url -> Tab cache

    def ensure_browser(self) -> None:
        """Ensure browser connection is active."""
        if not self.browser:
            self.browser = pychrome.Browser(url=f"http://localhost:{self.port}")

    def list_targets(self) -> list[dict]:
        """List available CDP targets (tabs)."""
        url = f"http://localhost:{self.port}/json"
        with urllib.request.urlopen(url) as response:
            targets = json_module.loads(response.read().decode())
        return [
            {"index": i, "url": t.get("url", ""), "ws_url": t.get("webSocketDebuggerUrl", "")}
            for i, t in enumerate(targets)
            if t.get("type") == "page"
        ]

    def get_tab(self, target: int | str) -> pychrome.Tab:
        """Get tab by index or ws_url, with caching."""
        self.ensure_browser()
        tabs = self.browser.list_tab()
        if not tabs:
            raise ConnectionError("No Tabby tabs found")

        # Resolve target to tab
        if isinstance(target, int):
            tab = tabs[target]  # supports -1 for last
        else:
            tab = None
            for t in tabs:
                if t.websocket_url == target:
                    tab = t
                    break
            if not tab:
                raise ValueError(f"Target not found: {target}")

        # Cache by ws_url
        ws_url = tab.websocket_url
        if ws_url not in self._tabs:
            tab.start()
            self._tabs[ws_url] = tab

        return self._tabs[ws_url]

    def disconnect(self) -> None:
        """Close all CDP connections."""
        for tab in self._tabs.values():
            try:
                tab.stop()
            except Exception:
                pass
        self._tabs.clear()
        self.browser = None

    def execute_js(self, expression: str, target: int | str) -> Any:
        """Execute JavaScript in Tabby context and return result."""
        tab = self.get_tab(target)
        result = tab.Runtime.evaluate(expression=expression, returnByValue=True)
        if "exceptionDetails" in result:
            raise RuntimeError(result["exceptionDetails"]["text"])
        return result.get("result", {}).get("value")

    def query(self, selector: str, target: int | str) -> list[dict]:
        """Query elements by CSS selector, return list with element info."""
        js = f"""
        (() => {{
            const elements = document.querySelectorAll({repr(selector)});
            return Array.from(elements).map((el, i) => ({{
                index: i,
                tagName: el.tagName.toLowerCase(),
                id: el.id || null,
                className: el.className || null,
                textContent: el.textContent?.substring(0, 100) || null,
                innerText: el.innerText?.substring(0, 100) || null
            }}));
        }})()
        """
        return self.execute_js(js, target) or []

    def click(self, selector: str, target: int | str, index: int = 0) -> bool:
        """Click element matching selector."""
        js = f"""
        (() => {{
            const elements = document.querySelectorAll({repr(selector)});
            if (elements[{index}]) {{
                elements[{index}].click();
                return true;
            }}
            return false;
        }})()
        """
        return self.execute_js(js, target)

    def get_text(self, selector: str, target: int | str) -> str | None:
        """Get text content of element."""
        js = f"""
        (() => {{
            const el = document.querySelector({repr(selector)});
            return el ? el.textContent : null;
        }})()
        """
        return self.execute_js(js, target)

    def wait_for(self, selector: str, target: int | str, timeout: float = 5.0) -> bool:
        """Wait for element to exist, return True if found."""
        start = time.time()
        while time.time() - start < timeout:
            js = f"document.querySelector({repr(selector)}) !== null"
            if self.execute_js(js, target):
                return True
            time.sleep(0.1)
        return False

    def screenshot(self, target: int | str, format: str = "png", quality: int = 80) -> str:
        """Capture screenshot, return base64 encoded image."""
        tab = self.get_tab(target)
        params: dict[str, Any] = {"format": format}
        if format == "jpeg":
            params["quality"] = quality
        result = tab.Page.captureScreenshot(**params)
        return result["data"]


# Global connection instance
_connection: TabbyConnection | None = None


def get_connection(port: int = 9222) -> TabbyConnection:
    """Get or create global connection instance."""
    global _connection
    if _connection is None:
        _connection = TabbyConnection(port)
    return _connection
