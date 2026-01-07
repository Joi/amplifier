---
name: browser
description: Browser automation via Playwright. Use when user needs to automate web interactions, scrape pages, take screenshots, or test web applications.
version: 1.0.0
---

# Browser Skill

Full browser automation using Playwright. Replaces the `@playwright/mcp` server with a native Python implementation.

## When to Use

- User asks to "open a webpage" or "navigate to URL"
- User needs to scrape/extract content from a website
- User wants to automate form filling or clicking
- User needs screenshots of web pages
- User wants to test web interactions
- User mentions browser automation or Playwright

## Python API (Preferred)

### Basic Usage

```python
from amplifier.skills.browser import Browser, BrowserConfig

# Simple usage with context manager
async with Browser() as browser:
    await browser.goto("https://example.com")
    title = await browser.title()
    content = await browser.text_content("main")
    print(f"Title: {title}")

# With configuration
config = BrowserConfig(
    headless=True,          # Run without visible window
    browser_type="chromium", # or "firefox", "webkit"
    isolated=True,          # Use temp profile (no persistence)
)
async with Browser(config) as browser:
    await browser.goto("https://example.com")
```

### Navigation

```python
await browser.goto("https://example.com")
await browser.back()
await browser.forward()
await browser.reload()

url = await browser.url()
title = await browser.title()
```

### Interactions

```python
# Click
await browser.click("button.submit")
await browser.click("text=Login")  # Click by text
await browser.double_click("#item")

# Fill forms
await browser.fill("input[name=email]", "user@example.com")
await browser.fill("input[name=password]", "secret")
await browser.press("Enter")

# Type slowly (triggers key events)
await browser.type("#search", "query", delay=50)

# Select dropdowns
await browser.select("select#country", "JP")

# Checkboxes
await browser.check("#agree")
await browser.uncheck("#newsletter")

# Hover
await browser.hover(".menu-item")

# Scroll
await browser.scroll(y=500)  # Scroll down
await browser.scroll(selector=".container", y=200)
```

### Page Content

```python
# Get content
html = await browser.content()
text = await browser.text_content("article")

# Structured snapshot
snapshot = await browser.snapshot()
print(snapshot.title)
print(snapshot.text_content)
print(snapshot.links)  # All links on page
print(snapshot.forms)  # All forms with inputs
```

### Screenshots & PDFs

```python
# Screenshot
await browser.screenshot(path="page.png")
await browser.screenshot(path="full.png", full_page=True)
await browser.screenshot(selector="#chart", path="chart.png")

# Base64 (for embedding)
b64 = await browser.screenshot_base64()

# PDF (Chromium only)
await browser.pdf(path="page.pdf")
```

### JavaScript Execution

```python
# Evaluate expression
title = await browser.evaluate("document.title")
count = await browser.evaluate("document.querySelectorAll('a').length")

# Evaluate on element
text = await browser.evaluate_on("h1", "el => el.textContent")
```

### Waiting

```python
# Wait for element
await browser.wait_for(selector=".loaded")

# Wait for text
await browser.wait_for(text="Success!")

# Wait for URL
await browser.wait_for(url="**/dashboard")

# Wait for load state
await browser.wait_for_load("networkidle")
```

### Tabs

```python
# Open new tab
await browser.new_tab("https://other-site.com")

# List tabs
tabs = await browser.tabs()

# Switch tab
await browser.switch_tab(0)

# Close tab
await browser.close_tab()  # Current tab
await browser.close_tab(1)  # By index
```

### Cookies

```python
cookies = await browser.get_cookies()
await browser.set_cookie(name="session", value="abc123", domain=".example.com")
await browser.clear_cookies()
```

## Convenience Functions

```python
from amplifier.skills.browser import fetch_page, screenshot_url

# Quick page fetch
snapshot = await fetch_page("https://example.com")
print(snapshot.title)
print(snapshot.text_content)

# Quick screenshot
await screenshot_url("https://example.com", path="shot.png", full_page=True)
```

## CLI Interface

```bash
# Fetch page content
python -m amplifier.skills.browser fetch "https://example.com"
python -m amplifier.skills.browser fetch "https://example.com" --json

# Take screenshot
python -m amplifier.skills.browser screenshot "https://example.com" -o page.png
python -m amplifier.skills.browser screenshot "https://example.com" --full -o full.png

# Interactive browser
python -m amplifier.skills.browser interactive --url "https://example.com"
```

## Configuration Options

```python
BrowserConfig(
    headless=False,          # Show browser window (default)
    browser_type="chromium", # Browser engine
    user_data_dir=None,      # Custom profile path
    viewport_width=1280,     # Window width
    viewport_height=720,     # Window height
    timeout_ms=30000,        # Default timeout
    isolated=False,          # Use temp profile
)
```

## Browser Profiles

By default, the skill uses a persistent profile at:
```
~/Library/Caches/ms-playwright/amplifier-profile
```

This means logged-in sessions persist between runs. Use `isolated=True` for clean sessions.

## Requirements

Playwright browsers must be installed:
```bash
playwright install chromium  # or firefox, webkit
```

## Advantages Over MCP

- ✅ Works in subagents (MCP tools don't inherit)
- ✅ Full Playwright API access (not limited to MCP tools)
- ✅ No Node.js dependency
- ✅ Works in scripts, cron jobs, SDK calls
- ✅ Proper async/await patterns
- ✅ Direct access to Page object for advanced use
