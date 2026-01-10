"""CDP connection and helper methods for Tabby."""

import time
from typing import Any

import pychrome


class TabbyConnection:
    """Manages CDP connection to Tabby terminal."""

    def __init__(self, port: int = 9222):
        self.port = port
        self.browser: pychrome.Browser | None = None
        self.tab: pychrome.Tab | None = None

    def connect(self) -> None:
        """Establish CDP connection to Tabby."""
        self.browser = pychrome.Browser(url=f"http://localhost:{self.port}")
        tabs = self.browser.list_tab()
        if not tabs:
            raise ConnectionError("No Tabby tabs found")
        self.tab = tabs[0]
        self.tab.start()

    def disconnect(self) -> None:
        """Close CDP connection."""
        if self.tab:
            self.tab.stop()
            self.tab = None
        self.browser = None

    def ensure_connected(self) -> None:
        """Ensure connection is active, reconnect if needed."""
        if not self.tab:
            self.connect()

    def execute_js(self, expression: str) -> Any:
        """Execute JavaScript in Tabby context and return result."""
        self.ensure_connected()
        result = self.tab.Runtime.evaluate(expression=expression, returnByValue=True)
        if "exceptionDetails" in result:
            raise RuntimeError(result["exceptionDetails"]["text"])
        return result.get("result", {}).get("value")

    def query(self, selector: str) -> list[dict]:
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
        return self.execute_js(js) or []

    def click(self, selector: str, index: int = 0) -> bool:
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
        return self.execute_js(js)

    def get_text(self, selector: str) -> str | None:
        """Get text content of element."""
        js = f"""
        (() => {{
            const el = document.querySelector({repr(selector)});
            return el ? el.textContent : null;
        }})()
        """
        return self.execute_js(js)

    def wait_for(self, selector: str, timeout: float = 5.0) -> bool:
        """Wait for element to exist, return True if found."""
        start = time.time()
        while time.time() - start < timeout:
            js = f"document.querySelector({repr(selector)}) !== null"
            if self.execute_js(js):
                return True
            time.sleep(0.1)
        return False


# Global connection instance
_connection: TabbyConnection | None = None


def get_connection(port: int = 9222) -> TabbyConnection:
    """Get or create global connection instance."""
    global _connection
    if _connection is None:
        _connection = TabbyConnection(port)
    return _connection
