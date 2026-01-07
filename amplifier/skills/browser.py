"""Browser automation skill using Playwright.

Native Amplifier skill for browser automation. Works everywhere:
main session, subagents, SDK, scripts, cron jobs.

Usage:
    from amplifier.skills.browser import Browser

    async with Browser() as browser:
        # Navigate and interact
        await browser.goto("https://example.com")
        await browser.click("text=Login")
        await browser.fill("input[name=email]", "user@example.com")
        
        # Get page content
        content = await browser.text_content("main")
        screenshot = await browser.screenshot()
        
        # Run custom Playwright code
        title = await browser.evaluate("document.title")
"""

from __future__ import annotations

import asyncio
import base64
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

from playwright.async_api import Browser as PlaywrightBrowser
from playwright.async_api import BrowserContext, Page, async_playwright

# Default browser profile location (matches Playwright MCP)
DEFAULT_USER_DATA_DIR = Path.home() / "Library/Caches/ms-playwright/amplifier-profile"


@dataclass
class BrowserConfig:
    """Browser configuration options."""

    headless: bool = False
    browser_type: Literal["chromium", "firefox", "webkit"] = "chromium"
    user_data_dir: Path | str | None = None
    viewport_width: int = 1280
    viewport_height: int = 720
    timeout_ms: int = 30000
    isolated: bool = False  # If True, use temp profile instead of persistent


@dataclass
class PageSnapshot:
    """Represents a page snapshot."""

    url: str
    title: str
    text_content: str
    links: list[dict[str, str]] = field(default_factory=list)
    forms: list[dict[str, Any]] = field(default_factory=list)


class Browser:
    """Async browser automation using Playwright.

    Example:
        async with Browser() as browser:
            await browser.goto("https://example.com")
            title = await browser.title()
            print(title)
    """

    def __init__(self, config: BrowserConfig | None = None):
        """Initialize browser with optional configuration.

        Args:
            config: Browser configuration. Uses defaults if not provided.
        """
        self.config = config or BrowserConfig()
        self._playwright = None
        self._browser: PlaywrightBrowser | None = None
        self._context: BrowserContext | None = None
        self._page: Page | None = None

    async def __aenter__(self) -> "Browser":
        """Start browser session."""
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Close browser session."""
        await self.close()

    async def start(self) -> None:
        """Start the browser."""
        self._playwright = await async_playwright().start()

        browser_type = getattr(self._playwright, self.config.browser_type)

        if self.config.isolated:
            # Launch without persistent context
            self._browser = await browser_type.launch(headless=self.config.headless)
            self._context = await self._browser.new_context(
                viewport={
                    "width": self.config.viewport_width,
                    "height": self.config.viewport_height,
                }
            )
        else:
            # Use persistent context
            user_data_dir = self.config.user_data_dir or DEFAULT_USER_DATA_DIR
            Path(user_data_dir).mkdir(parents=True, exist_ok=True)

            self._context = await browser_type.launch_persistent_context(
                user_data_dir=str(user_data_dir),
                headless=self.config.headless,
                viewport={
                    "width": self.config.viewport_width,
                    "height": self.config.viewport_height,
                },
            )

        self._page = await self._context.new_page()
        self._page.set_default_timeout(self.config.timeout_ms)

    async def close(self) -> None:
        """Close the browser."""
        if self._context:
            await self._context.close()
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()

    @property
    def page(self) -> Page:
        """Get the current page."""
        if not self._page:
            raise RuntimeError("Browser not started. Use 'async with Browser()' or call start().")
        return self._page

    @property
    def context(self) -> BrowserContext:
        """Get the browser context."""
        if not self._context:
            raise RuntimeError("Browser not started.")
        return self._context

    # =========================================================================
    # Navigation
    # =========================================================================

    async def goto(self, url: str, wait_until: str = "domcontentloaded") -> None:
        """Navigate to a URL.

        Args:
            url: URL to navigate to
            wait_until: When to consider navigation complete
                        ("domcontentloaded", "load", "networkidle")
        """
        await self.page.goto(url, wait_until=wait_until)

    async def back(self) -> None:
        """Go back in history."""
        await self.page.go_back()

    async def forward(self) -> None:
        """Go forward in history."""
        await self.page.go_forward()

    async def reload(self) -> None:
        """Reload the page."""
        await self.page.reload()

    # =========================================================================
    # Page Information
    # =========================================================================

    async def url(self) -> str:
        """Get current URL."""
        return self.page.url

    async def title(self) -> str:
        """Get page title."""
        return await self.page.title()

    async def content(self) -> str:
        """Get full page HTML."""
        return await self.page.content()

    async def text_content(self, selector: str = "body") -> str:
        """Get text content of an element.

        Args:
            selector: CSS selector (default: body)

        Returns:
            Text content of the element
        """
        element = await self.page.query_selector(selector)
        if element:
            return await element.text_content() or ""
        return ""

    async def snapshot(self) -> PageSnapshot:
        """Get a structured snapshot of the page.

        Returns:
            PageSnapshot with URL, title, text, links, and forms
        """
        url = self.page.url
        title = await self.page.title()
        text = await self.text_content("body")

        # Extract links
        links = await self.page.evaluate("""
            () => Array.from(document.querySelectorAll('a[href]')).map(a => ({
                text: a.textContent?.trim() || '',
                href: a.href
            })).filter(l => l.text && l.href)
        """)

        # Extract forms
        forms = await self.page.evaluate("""
            () => Array.from(document.querySelectorAll('form')).map(f => ({
                action: f.action,
                method: f.method,
                inputs: Array.from(f.querySelectorAll('input, select, textarea')).map(i => ({
                    name: i.name,
                    type: i.type || i.tagName.toLowerCase(),
                    placeholder: i.placeholder || ''
                }))
            }))
        """)

        return PageSnapshot(url=url, title=title, text_content=text, links=links, forms=forms)

    # =========================================================================
    # Interactions
    # =========================================================================

    async def click(self, selector: str, **kwargs) -> None:
        """Click an element.

        Args:
            selector: CSS selector, text selector ("text=Click me"), or role selector
            **kwargs: Additional click options (button, click_count, delay, etc.)
        """
        await self.page.click(selector, **kwargs)

    async def double_click(self, selector: str, **kwargs) -> None:
        """Double-click an element."""
        await self.page.dblclick(selector, **kwargs)

    async def fill(self, selector: str, value: str) -> None:
        """Fill a text input.

        Args:
            selector: CSS selector for the input
            value: Text to fill
        """
        await self.page.fill(selector, value)

    async def type(self, selector: str, text: str, delay: int = 50) -> None:
        """Type text character by character (triggers key events).

        Args:
            selector: CSS selector for the input
            text: Text to type
            delay: Delay between keystrokes in ms
        """
        await self.page.type(selector, text, delay=delay)

    async def press(self, key: str, selector: str | None = None) -> None:
        """Press a keyboard key.

        Args:
            key: Key to press (e.g., "Enter", "Tab", "ArrowDown")
            selector: Optional element to focus first
        """
        if selector:
            await self.page.press(selector, key)
        else:
            await self.page.keyboard.press(key)

    async def select(self, selector: str, value: str | list[str]) -> None:
        """Select option(s) in a dropdown.

        Args:
            selector: CSS selector for the select element
            value: Value or list of values to select
        """
        values = [value] if isinstance(value, str) else value
        await self.page.select_option(selector, values)

    async def check(self, selector: str) -> None:
        """Check a checkbox."""
        await self.page.check(selector)

    async def uncheck(self, selector: str) -> None:
        """Uncheck a checkbox."""
        await self.page.uncheck(selector)

    async def hover(self, selector: str) -> None:
        """Hover over an element."""
        await self.page.hover(selector)

    async def scroll(self, selector: str | None = None, x: int = 0, y: int = 0) -> None:
        """Scroll the page or an element.

        Args:
            selector: Optional element to scroll (scrolls page if None)
            x: Horizontal scroll amount
            y: Vertical scroll amount
        """
        if selector:
            await self.page.evaluate(
                f"document.querySelector('{selector}').scrollBy({x}, {y})"
            )
        else:
            await self.page.evaluate(f"window.scrollBy({x}, {y})")

    async def upload_file(self, selector: str, files: str | list[str]) -> None:
        """Upload file(s) to a file input.

        Args:
            selector: CSS selector for the file input
            files: File path or list of file paths
        """
        file_list = [files] if isinstance(files, str) else files
        await self.page.set_input_files(selector, file_list)

    # =========================================================================
    # Waiting
    # =========================================================================

    async def wait_for(
        self,
        selector: str | None = None,
        text: str | None = None,
        url: str | None = None,
        timeout: int | None = None,
    ) -> None:
        """Wait for a condition.

        Args:
            selector: Wait for element to appear
            text: Wait for text to appear on page
            url: Wait for URL to match (supports glob patterns)
            timeout: Custom timeout in ms
        """
        opts = {"timeout": timeout} if timeout else {}

        if selector:
            await self.page.wait_for_selector(selector, **opts)
        elif text:
            await self.page.wait_for_selector(f"text={text}", **opts)
        elif url:
            await self.page.wait_for_url(url, **opts)

    async def wait_for_load(self, state: str = "domcontentloaded") -> None:
        """Wait for page load state.

        Args:
            state: Load state ("domcontentloaded", "load", "networkidle")
        """
        await self.page.wait_for_load_state(state)

    # =========================================================================
    # Screenshots & PDFs
    # =========================================================================

    async def screenshot(
        self,
        path: str | None = None,
        full_page: bool = False,
        selector: str | None = None,
    ) -> bytes:
        """Take a screenshot.

        Args:
            path: Optional path to save the screenshot
            full_page: Capture full scrollable page
            selector: Optional element to screenshot

        Returns:
            Screenshot as bytes (PNG format)
        """
        opts: dict[str, Any] = {"full_page": full_page}
        if path:
            opts["path"] = path

        if selector:
            element = await self.page.query_selector(selector)
            if element:
                return await element.screenshot(**opts)
            raise ValueError(f"Element not found: {selector}")

        return await self.page.screenshot(**opts)

    async def screenshot_base64(self, **kwargs) -> str:
        """Take a screenshot and return as base64.

        Args:
            **kwargs: Same as screenshot()

        Returns:
            Base64-encoded PNG screenshot
        """
        data = await self.screenshot(**kwargs)
        return base64.b64encode(data).decode()

    async def pdf(self, path: str | None = None, **kwargs) -> bytes:
        """Generate PDF of the page (Chromium only).

        Args:
            path: Optional path to save the PDF
            **kwargs: Additional PDF options

        Returns:
            PDF as bytes
        """
        opts = kwargs.copy()
        if path:
            opts["path"] = path
        return await self.page.pdf(**opts)

    # =========================================================================
    # JavaScript Execution
    # =========================================================================

    async def evaluate(self, expression: str) -> Any:
        """Execute JavaScript and return the result.

        Args:
            expression: JavaScript expression to evaluate

        Returns:
            Result of the expression
        """
        return await self.page.evaluate(expression)

    async def evaluate_on(self, selector: str, expression: str) -> Any:
        """Execute JavaScript on an element.

        Args:
            selector: CSS selector for the element
            expression: JavaScript expression (element available as first arg)

        Returns:
            Result of the expression
        """
        return await self.page.eval_on_selector(selector, expression)

    # =========================================================================
    # Tabs
    # =========================================================================

    async def new_tab(self, url: str | None = None) -> Page:
        """Open a new tab.

        Args:
            url: Optional URL to navigate to

        Returns:
            The new page object
        """
        page = await self.context.new_page()
        if url:
            await page.goto(url)
        self._page = page
        return page

    async def tabs(self) -> list[Page]:
        """Get all open tabs."""
        return self.context.pages

    async def switch_tab(self, index: int) -> None:
        """Switch to a tab by index.

        Args:
            index: Tab index (0-based)
        """
        pages = self.context.pages
        if 0 <= index < len(pages):
            self._page = pages[index]
            await self._page.bring_to_front()
        else:
            raise IndexError(f"Tab index {index} out of range (0-{len(pages)-1})")

    async def close_tab(self, index: int | None = None) -> None:
        """Close a tab.

        Args:
            index: Tab index to close (closes current if None)
        """
        if index is not None:
            pages = self.context.pages
            if 0 <= index < len(pages):
                await pages[index].close()
            else:
                raise IndexError(f"Tab index {index} out of range")
        else:
            await self.page.close()

        # Switch to remaining tab if any
        pages = self.context.pages
        if pages:
            self._page = pages[-1]

    # =========================================================================
    # Network & Console
    # =========================================================================

    async def get_cookies(self) -> list[dict[str, Any]]:
        """Get all cookies."""
        return await self.context.cookies()

    async def set_cookie(self, **cookie) -> None:
        """Set a cookie.

        Args:
            **cookie: Cookie properties (name, value, url/domain, path, etc.)
        """
        await self.context.add_cookies([cookie])

    async def clear_cookies(self) -> None:
        """Clear all cookies."""
        await self.context.clear_cookies()

    # =========================================================================
    # Dialog Handling
    # =========================================================================

    def on_dialog(self, handler) -> None:
        """Set dialog handler.

        Args:
            handler: Async function that receives Dialog object

        Example:
            async def handle_dialog(dialog):
                await dialog.accept("my input")
            browser.on_dialog(handle_dialog)
        """
        self.page.on("dialog", handler)

    async def accept_dialogs(self, accept: bool = True) -> None:
        """Auto-accept or dismiss all dialogs.

        Args:
            accept: Whether to accept (True) or dismiss (False) dialogs
        """

        async def handler(dialog):
            if accept:
                await dialog.accept()
            else:
                await dialog.dismiss()

        self.page.on("dialog", handler)


# =============================================================================
# Convenience Functions
# =============================================================================


async def fetch_page(url: str, headless: bool = True) -> PageSnapshot:
    """Fetch a page and return a snapshot.

    Args:
        url: URL to fetch
        headless: Run in headless mode (default True)

    Returns:
        PageSnapshot with page content

    Example:
        snapshot = await fetch_page("https://example.com")
        print(snapshot.title)
        print(snapshot.text_content)
    """
    config = BrowserConfig(headless=headless, isolated=True)
    async with Browser(config) as browser:
        await browser.goto(url)
        return await browser.snapshot()


async def screenshot_url(url: str, path: str | None = None, full_page: bool = False) -> bytes:
    """Take a screenshot of a URL.

    Args:
        url: URL to screenshot
        path: Optional path to save
        full_page: Capture full page

    Returns:
        Screenshot bytes
    """
    config = BrowserConfig(headless=True, isolated=True)
    async with Browser(config) as browser:
        await browser.goto(url)
        return await browser.screenshot(path=path, full_page=full_page)


# =============================================================================
# CLI Interface
# =============================================================================


async def _cli_main() -> None:
    """CLI entry point."""
    import argparse
    import json

    parser = argparse.ArgumentParser(description="Browser automation via Playwright")
    subparsers = parser.add_subparsers(dest="command", help="Command")

    # fetch command
    fetch_p = subparsers.add_parser("fetch", help="Fetch page content")
    fetch_p.add_argument("url", help="URL to fetch")
    fetch_p.add_argument("--json", action="store_true", help="Output as JSON")

    # screenshot command
    shot_p = subparsers.add_parser("screenshot", help="Take screenshot")
    shot_p.add_argument("url", help="URL to screenshot")
    shot_p.add_argument("-o", "--output", help="Output file path")
    shot_p.add_argument("--full", action="store_true", help="Full page screenshot")

    # interactive command
    int_p = subparsers.add_parser("interactive", help="Start interactive browser")
    int_p.add_argument("--url", help="Initial URL")
    int_p.add_argument("--headless", action="store_true", help="Run headless")

    args = parser.parse_args()

    if args.command == "fetch":
        snapshot = await fetch_page(args.url)
        if args.json:
            print(
                json.dumps(
                    {
                        "url": snapshot.url,
                        "title": snapshot.title,
                        "text": snapshot.text_content[:2000],
                        "links": snapshot.links[:20],
                    },
                    indent=2,
                )
            )
        else:
            print(f"Title: {snapshot.title}")
            print(f"URL: {snapshot.url}")
            print(f"\nContent ({len(snapshot.text_content)} chars):")
            print(snapshot.text_content[:2000])
            if len(snapshot.text_content) > 2000:
                print("...")

    elif args.command == "screenshot":
        output = args.output or "screenshot.png"
        await screenshot_url(args.url, path=output, full_page=args.full)
        print(f"Screenshot saved to: {output}")

    elif args.command == "interactive":
        config = BrowserConfig(headless=args.headless)
        async with Browser(config) as browser:
            if args.url:
                await browser.goto(args.url)
            print("Browser started. Press Ctrl+C to close.")
            try:
                while True:
                    await asyncio.sleep(1)
            except KeyboardInterrupt:
                print("\nClosing browser...")

    else:
        parser.print_help()


if __name__ == "__main__":
    asyncio.run(_cli_main())
