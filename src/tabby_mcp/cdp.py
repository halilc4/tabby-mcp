"""CDP connection and helper methods for Tabby."""

import logging
import time
import urllib.request
import json as json_module
from typing import Any

import pychrome

logger = logging.getLogger(__name__)


class TabbyConnection:
    """Manages CDP connection to Tabby terminal."""

    def __init__(self, port: int = 9222):
        self.port = port
        self.browser: pychrome.Browser | None = None
        self._tabs: dict[str, pychrome.Tab] = {}  # ws_url -> Tab cache

    def ensure_browser(self) -> None:
        """Ensure browser connection is active."""
        if not self.browser:
            logger.info("Connecting to CDP at localhost:%d", self.port)
            self.browser = pychrome.Browser(url=f"http://localhost:{self.port}")

    def list_targets(self) -> list[dict]:
        """List available CDP targets (tabs)."""
        url = f"http://localhost:{self.port}/json"
        with urllib.request.urlopen(url) as response:
            targets = json_module.loads(response.read().decode())
        return [
            {
                "index": i,
                "title": t.get("title", ""),
                "url": t.get("url", ""),
                "ws_url": t.get("webSocketDebuggerUrl", ""),
            }
            for i, t in enumerate(targets)
            if t.get("type") == "page"
        ]

    def get_tab(self, target: int | str) -> pychrome.Tab:
        """Get tab by index or ws_url, with caching."""
        logger.debug("Getting tab: %s", target)
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

    def execute_js(self, expression: str, target: int | str, wrap: bool = True) -> Any:
        """Execute JavaScript in Tabby context and return result.

        Args:
            expression: JavaScript code to execute
            target: Tab index or ws_url
            wrap: If True (default), wraps code in async IIFE for fresh scope + await support.
                  Set to False for raw execution (e.g., defining global functions).
        """
        logger.debug("execute_js: %s", expression[:100])
        tab = self.get_tab(target)

        if wrap:
            expression = f"(async () => {{ {expression} }})()"

        result = tab.Runtime.evaluate(
            expression=expression,
            returnByValue=True,
            awaitPromise=wrap,
        )
        if "exceptionDetails" in result:
            error_text = result["exceptionDetails"].get("text", "Unknown error")
            exception = result["exceptionDetails"].get("exception", {})
            description = exception.get("description", "")
            logger.error("JS error: %s - %s", error_text, description)
            raise RuntimeError(f"{error_text}: {description}" if description else error_text)
        return result.get("result", {}).get("value")

    def query(
        self,
        selector: str,
        target: int | str,
        include_children: bool = False,
        include_text: bool = True,
    ) -> list[dict]:
        """Query elements by CSS selector, return list with element info."""
        logger.debug("query: selector=%s, children=%s, text=%s", selector, include_children, include_text)
        js = f"""
        (() => {{
            const elements = document.querySelectorAll({repr(selector)});
            return Array.from(elements).map((el, i) => {{
                const attrs = {{}};
                for (const attr of el.attributes) {{
                    attrs[attr.name] = attr.value;
                }}
                const result = {{
                    index: i,
                    tagName: el.tagName.toLowerCase(),
                    id: el.id || null,
                    className: el.className || null,
                    attributes: attrs,
                    childCount: el.children.length
                }};
                {"" if not include_children else '''
                result.children = Array.from(el.children).slice(0, 10).map(c => ({
                    tagName: c.tagName.toLowerCase(),
                    id: c.id || null,
                    className: c.className || null
                }));
                '''}
                {"" if not include_text else '''
                result.textContent = el.textContent?.substring(0, 200) || null;
                '''}
                return result;
            }});
        }})()
        """
        return self.execute_js(js, target) or []

    def query_with_retry(
        self,
        selector: str,
        target: int | str,
        max_retries: int = 3,
        retry_delay: float = 0.2,
        include_children: bool = False,
        include_text: bool = True,
    ) -> list[dict]:
        """Query with automatic retry for dynamic content (Angular *ngIf, lazy elements).

        Useful when elements are rendered asynchronously after an action.
        """
        for attempt in range(max_retries):
            result = self.query(selector, target, include_children, include_text)
            if result:
                return result
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
        return []

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

    def wait_for(
        self,
        selector: str,
        target: int | str,
        timeout: float = 5.0,
        visible: bool = False,
    ) -> bool:
        """Wait for element to exist (and optionally be visible).

        Args:
            selector: CSS selector
            target: Tab index or ws_url
            timeout: Max wait time in seconds
            visible: If True, also wait for element to have dimensions > 0
        """
        start = time.time()
        while time.time() - start < timeout:
            if visible:
                js = f"""
                (() => {{
                    const el = document.querySelector({repr(selector)});
                    if (!el) return false;
                    const rect = el.getBoundingClientRect();
                    return rect.width > 0 && rect.height > 0;
                }})()
                """
            else:
                js = f"document.querySelector({repr(selector)}) !== null"
            if self.execute_js(js, target):
                return True
            time.sleep(0.1)
        return False

    def wait_for_angular(self, target: int | str, timeout: float = 2.0) -> bool:
        """Wait for Angular to finish rendering (Zone.js stable).

        Uses Angular's testability API to check if all pending async operations are done.
        Returns True immediately if app is not Angular or has no testabilities.
        """
        js = """
        (() => {
            const ng = window.getAllAngularTestabilities?.();
            if (!ng || ng.length === 0) return true;
            return ng.every(t => t.isStable());
        })()
        """
        start = time.time()
        while time.time() - start < timeout:
            try:
                if self.execute_js(js, target):
                    return True
            except Exception:
                pass
            time.sleep(0.05)
        return True  # Timeout - proceed anyway

    def screenshot(self, target: int | str, format: str = "png", quality: int = 80) -> str:
        """Capture screenshot, return base64 encoded image."""
        logger.debug("screenshot: format=%s, quality=%d", format, quality)
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
