"""CDP connection and helper methods for Tabby."""

import logging
import threading
import time
import urllib.request
import json as json_module
from typing import Any

import pychrome

logger = logging.getLogger(__name__)


def _safe_selector(selector: str) -> str:
    """Escape selector for safe JS embedding."""
    return json_module.dumps(selector)


def _js_iife(body: str) -> str:
    """Wrap JS body in IIFE for isolated scope."""
    return f"(() => {{ {body} }})()"


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

        # For ws_url string, check cache first then fetch directly
        if isinstance(target, str):
            if target in self._tabs:
                return self._tabs[target]

            # Verify ws_url exists via /json endpoint
            url = f"http://localhost:{self.port}/json"
            with urllib.request.urlopen(url) as response:
                targets = json_module.loads(response.read().decode())

            for t in targets:
                if t.get("webSocketDebuggerUrl") == target:
                    tab = pychrome.Tab(webSocketDebuggerUrl=target)
                    tab.start()
                    self._tabs[target] = tab
                    return tab

            raise ValueError(f"Target not found: {target}")

        # For index, use browser.list_tab()
        self.ensure_browser()
        tabs = self.browser.list_tab()
        if not tabs:
            raise ConnectionError("No Tabby tabs found")

        tab = tabs[target]  # supports -1 for last
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
            except Exception as e:
                logger.debug("Failed to stop tab: %s", e)
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
        children_js = """
                result.children = Array.from(el.children).slice(0, 10).map(c => ({
                    tagName: c.tagName.toLowerCase(),
                    id: c.id || null,
                    className: c.className || null
                }));""" if include_children else ""
        text_js = """
                result.textContent = el.textContent?.substring(0, 200) || null;""" if include_text else ""
        js = _js_iife(f"""
            const elements = document.querySelectorAll({_safe_selector(selector)});
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
                }};{children_js}{text_js}
                return result;
            }});
        """)
        return self.execute_js(js, target, wrap=False) or []

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
        js = _js_iife(f"""
            const elements = document.querySelectorAll({_safe_selector(selector)});
            if (elements[{index}]) {{
                elements[{index}].click();
                return true;
            }}
            return false;
        """)
        return self.execute_js(js, target, wrap=False)

    def get_text(self, selector: str, target: int | str) -> str | None:
        """Get text content of element."""
        js = _js_iife(f"""
            const el = document.querySelector({_safe_selector(selector)});
            return el ? el.textContent : null;
        """)
        return self.execute_js(js, target, wrap=False)

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
        safe = _safe_selector(selector)
        start = time.time()
        while time.time() - start < timeout:
            if visible:
                js = _js_iife(f"""
                    const el = document.querySelector({safe});
                    if (!el) return false;
                    const rect = el.getBoundingClientRect();
                    return rect.width > 0 && rect.height > 0;
                """)
                if self.execute_js(js, target, wrap=False):
                    return True
            else:
                js = f"document.querySelector({safe}) !== null"
            if self.execute_js(js, target, wrap=False):
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
                if self.execute_js(js, target, wrap=False):
                    return True
            except Exception as e:
                logger.debug("Angular check failed: %s", e)
            time.sleep(0.05)
        return True  # Timeout - proceed anyway

    def screenshot(self, target: int | str, format: str = "jpeg", quality: int = 80) -> str:
        """Capture screenshot, return base64 encoded image.

        Image is scaled down if either dimension exceeds 2000px.
        Accounts for devicePixelRatio (Windows scaling).
        """
        logger.debug("screenshot: format=%s, quality=%d", format, quality)
        tab = self.get_tab(target)

        # Get viewport dimensions (CSS pixels)
        metrics = tab.Page.getLayoutMetrics()
        css_width = metrics["cssLayoutViewport"]["clientWidth"]
        css_height = metrics["cssLayoutViewport"]["clientHeight"]

        # Get devicePixelRatio (Windows scaling factor)
        dpr_result = tab.Runtime.evaluate(expression="window.devicePixelRatio")
        dpr = dpr_result.get("result", {}).get("value", 1)

        # Calculate actual pixel dimensions
        actual_width = css_width * dpr
        actual_height = css_height * dpr

        # Calculate scale to fit within 2000px (based on actual pixels)
        scale = min(1.0, 2000 / actual_width, 2000 / actual_height)

        params: dict[str, Any] = {"format": format}
        if format == "jpeg":
            params["quality"] = quality

        # Apply clip with scale if needed
        if scale < 1.0:
            logger.debug(
                "Scaling screenshot: %dx%d (dpr=%.2f, actual=%dx%d) -> scale=%.2f",
                css_width, css_height, dpr, int(actual_width), int(actual_height), scale
            )
            params["clip"] = {
                "x": 0,
                "y": 0,
                "width": css_width,
                "height": css_height,
                "scale": scale,
            }

        result = tab.Page.captureScreenshot(**params)
        return result["data"]


# Global connection instance
_connection: TabbyConnection | None = None
_connection_lock = threading.Lock()


def get_connection(port: int = 9222) -> TabbyConnection:
    """Get or create global connection instance (thread-safe)."""
    global _connection
    with _connection_lock:
        if _connection is None:
            _connection = TabbyConnection(port)
        elif _connection.port != port:
            raise ValueError(
                f"Connection already exists on port {_connection.port}, "
                f"cannot create on port {port}"
            )
        return _connection
