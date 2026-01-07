"""Notion API integration skill.

Native Amplifier skill that integrates with the secrets management system.
Works everywhere: main session, subagents, SDK, scripts, cron jobs.

Usage:
    from amplifier.skills.notion import search, get_page, create_page, query_database

    # Search for pages and databases
    results = await search("project notes")
    
    # Get page content
    page = await get_page("page-id-here")
    
    # Create a new page
    page = await create_page(
        parent_id="database-or-page-id",
        title="My New Page",
        content="Page content in markdown"
    )
    
    # Query a database
    rows = await query_database("database-id", filter={"property": "Status", "status": {"equals": "Done"}})
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any

import httpx

from amplifier.utils.secrets import get_notion_token

# API Configuration
BASE_URL = "https://api.notion.com/v1"
NOTION_VERSION = "2022-06-28"


@dataclass
class NotionObject:
    """Base class for Notion objects."""

    id: str
    object_type: str
    url: str | None = None
    created_time: str | None = None
    last_edited_time: str | None = None


@dataclass
class NotionPage(NotionObject):
    """Represents a Notion page."""

    title: str = "Untitled"
    parent_type: str | None = None
    parent_id: str | None = None
    properties: dict[str, Any] = field(default_factory=dict)
    content_blocks: list[dict[str, Any]] = field(default_factory=list)

    @classmethod
    def from_api(cls, data: dict[str, Any], blocks: list[dict] | None = None) -> NotionPage:
        """Create NotionPage from API response."""
        # Extract title from properties
        title = "Untitled"
        props = data.get("properties", {})
        
        # Try different title property names
        for prop_name in ["title", "Title", "Name", "name"]:
            if prop_name in props:
                prop_data = props[prop_name]
                if prop_data.get("type") == "title":
                    title_arr = prop_data.get("title", [])
                    if title_arr:
                        title = "".join(t.get("plain_text", "") for t in title_arr)
                    break

        # Extract parent info
        parent = data.get("parent", {})
        parent_type = parent.get("type")
        parent_id = parent.get(parent_type) if parent_type else None

        return cls(
            id=data.get("id", ""),
            object_type="page",
            url=data.get("url"),
            created_time=data.get("created_time"),
            last_edited_time=data.get("last_edited_time"),
            title=title,
            parent_type=parent_type,
            parent_id=parent_id,
            properties=props,
            content_blocks=blocks or [],
        )

    def __str__(self) -> str:
        return f"Page: {self.title} ({self.id[:8]}...)"


@dataclass
class NotionDatabase(NotionObject):
    """Represents a Notion database."""

    title: str = "Untitled"
    description: str | None = None
    properties_schema: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> NotionDatabase:
        """Create NotionDatabase from API response."""
        title_arr = data.get("title", [])
        title = "".join(t.get("plain_text", "") for t in title_arr) if title_arr else "Untitled"
        
        desc_arr = data.get("description", [])
        description = "".join(t.get("plain_text", "") for t in desc_arr) if desc_arr else None

        return cls(
            id=data.get("id", ""),
            object_type="database",
            url=data.get("url"),
            created_time=data.get("created_time"),
            last_edited_time=data.get("last_edited_time"),
            title=title,
            description=description,
            properties_schema=data.get("properties", {}),
        )

    def __str__(self) -> str:
        return f"Database: {self.title} ({self.id[:8]}...)"


async def _get_client() -> tuple[httpx.AsyncClient, dict[str, str]]:
    """Get HTTP client with authentication headers."""
    token = get_notion_token()
    headers = {
        "Authorization": f"Bearer {token}",
        "Notion-Version": NOTION_VERSION,
        "Content-Type": "application/json",
    }
    return httpx.AsyncClient(timeout=30), headers


async def search(
    query: str = "",
    filter_type: str | None = None,
    page_size: int = 10,
) -> list[NotionPage | NotionDatabase]:
    """Search for pages and databases in Notion.

    Args:
        query: Search query (empty string returns recent items)
        filter_type: Filter by "page" or "database" (None for both)
        page_size: Maximum number of results (default 10, max 100)

    Returns:
        List of NotionPage and/or NotionDatabase objects

    Example:
        results = await search("meeting notes")
        for r in results:
            print(r)
    """
    client, headers = await _get_client()

    payload: dict[str, Any] = {
        "query": query,
        "page_size": min(page_size, 100),
    }

    if filter_type in ("page", "database"):
        payload["filter"] = {"property": "object", "value": filter_type}

    async with client:
        resp = await client.post(f"{BASE_URL}/search", headers=headers, json=payload)
        resp.raise_for_status()
        data = resp.json()

    results: list[NotionPage | NotionDatabase] = []
    for item in data.get("results", []):
        if item.get("object") == "page":
            results.append(NotionPage.from_api(item))
        elif item.get("object") == "database":
            results.append(NotionDatabase.from_api(item))

    return results


async def get_page(page_id: str, include_content: bool = True) -> NotionPage | None:
    """Get a page by ID with optional content blocks.

    Args:
        page_id: The Notion page ID (with or without dashes)
        include_content: Whether to fetch page content blocks

    Returns:
        NotionPage object or None if not found

    Example:
        page = await get_page("12345678-1234-1234-1234-123456789012")
        print(page.title)
        for block in page.content_blocks:
            print(block)
    """
    client, headers = await _get_client()

    async with client:
        try:
            # Get page metadata
            resp = await client.get(f"{BASE_URL}/pages/{page_id}", headers=headers)
            resp.raise_for_status()
            page_data = resp.json()

            # Get content blocks if requested
            blocks = []
            if include_content:
                resp = await client.get(
                    f"{BASE_URL}/blocks/{page_id}/children",
                    headers=headers,
                    params={"page_size": 100},
                )
                resp.raise_for_status()
                blocks = resp.json().get("results", [])

            return NotionPage.from_api(page_data, blocks)

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return None
            raise


async def get_database(database_id: str) -> NotionDatabase | None:
    """Get a database by ID.

    Args:
        database_id: The Notion database ID

    Returns:
        NotionDatabase object or None if not found
    """
    client, headers = await _get_client()

    async with client:
        try:
            resp = await client.get(f"{BASE_URL}/databases/{database_id}", headers=headers)
            resp.raise_for_status()
            return NotionDatabase.from_api(resp.json())
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return None
            raise


async def query_database(
    database_id: str,
    filter: dict[str, Any] | None = None,
    sorts: list[dict[str, Any]] | None = None,
    page_size: int = 100,
) -> list[NotionPage]:
    """Query a database with optional filters and sorts.

    Args:
        database_id: The Notion database ID
        filter: Notion filter object (see Notion API docs)
        sorts: List of sort objects
        page_size: Maximum results per page

    Returns:
        List of NotionPage objects (database rows)

    Example:
        # Get all done tasks
        rows = await query_database(
            "database-id",
            filter={"property": "Status", "status": {"equals": "Done"}}
        )
        
        # Sort by date
        rows = await query_database(
            "database-id",
            sorts=[{"property": "Date", "direction": "descending"}]
        )
    """
    client, headers = await _get_client()

    payload: dict[str, Any] = {"page_size": min(page_size, 100)}
    if filter:
        payload["filter"] = filter
    if sorts:
        payload["sorts"] = sorts

    async with client:
        resp = await client.post(
            f"{BASE_URL}/databases/{database_id}/query",
            headers=headers,
            json=payload,
        )
        resp.raise_for_status()
        data = resp.json()

    return [NotionPage.from_api(item) for item in data.get("results", [])]


def _markdown_to_blocks(content: str) -> list[dict[str, Any]]:
    """Convert simple markdown to Notion blocks.
    
    Supports:
    - Paragraphs
    - Headers (# ## ###)
    - Bullet lists (- or *)
    - Numbered lists (1. 2. 3.)
    - Code blocks (```)
    """
    blocks = []
    lines = content.split("\n")
    i = 0
    
    while i < len(lines):
        line = lines[i]
        
        # Skip empty lines
        if not line.strip():
            i += 1
            continue
        
        # Code block
        if line.strip().startswith("```"):
            language = line.strip()[3:] or "plain text"
            code_lines = []
            i += 1
            while i < len(lines) and not lines[i].strip().startswith("```"):
                code_lines.append(lines[i])
                i += 1
            blocks.append({
                "object": "block",
                "type": "code",
                "code": {
                    "rich_text": [{"type": "text", "text": {"content": "\n".join(code_lines)}}],
                    "language": language,
                },
            })
            i += 1
            continue
        
        # Headers
        if line.startswith("### "):
            blocks.append({
                "object": "block",
                "type": "heading_3",
                "heading_3": {"rich_text": [{"type": "text", "text": {"content": line[4:]}}]},
            })
        elif line.startswith("## "):
            blocks.append({
                "object": "block",
                "type": "heading_2",
                "heading_2": {"rich_text": [{"type": "text", "text": {"content": line[3:]}}]},
            })
        elif line.startswith("# "):
            blocks.append({
                "object": "block",
                "type": "heading_1",
                "heading_1": {"rich_text": [{"type": "text", "text": {"content": line[2:]}}]},
            })
        # Bullet list
        elif line.strip().startswith("- ") or line.strip().startswith("* "):
            text = line.strip()[2:]
            blocks.append({
                "object": "block",
                "type": "bulleted_list_item",
                "bulleted_list_item": {"rich_text": [{"type": "text", "text": {"content": text}}]},
            })
        # Numbered list
        elif line.strip() and line.strip()[0].isdigit() and ". " in line:
            text = line.strip().split(". ", 1)[1] if ". " in line else line
            blocks.append({
                "object": "block",
                "type": "numbered_list_item",
                "numbered_list_item": {"rich_text": [{"type": "text", "text": {"content": text}}]},
            })
        # Paragraph
        else:
            blocks.append({
                "object": "block",
                "type": "paragraph",
                "paragraph": {"rich_text": [{"type": "text", "text": {"content": line}}]},
            })
        
        i += 1
    
    return blocks


async def create_page(
    parent_id: str,
    title: str,
    content: str | None = None,
    properties: dict[str, Any] | None = None,
    parent_type: str = "database_id",
) -> NotionPage:
    """Create a new page in Notion.

    Args:
        parent_id: Parent database or page ID
        title: Page title
        content: Optional markdown content for the page body
        properties: Additional properties (for database pages)
        parent_type: "database_id" or "page_id"

    Returns:
        Created NotionPage object

    Example:
        # Create in database
        page = await create_page(
            parent_id="database-id",
            title="Meeting Notes",
            content="## Attendees\\n- Alice\\n- Bob"
        )
        
        # Create as subpage
        page = await create_page(
            parent_id="page-id",
            title="Subpage",
            parent_type="page_id"
        )
    """
    client, headers = await _get_client()

    # Build properties with title
    props = properties.copy() if properties else {}
    
    # Set title property (use "title" for database pages, "Name" is also common)
    if parent_type == "database_id":
        # For database pages, we need to know the title property name
        # Default to common names
        if "title" not in props and "Title" not in props and "Name" not in props:
            props["Name"] = {"title": [{"text": {"content": title}}]}
    else:
        # For page children, use child_page type
        pass

    payload: dict[str, Any] = {
        "parent": {parent_type: parent_id},
        "properties": props if parent_type == "database_id" else {
            "title": [{"text": {"content": title}}]
        },
    }

    # Add content blocks if provided
    if content:
        payload["children"] = _markdown_to_blocks(content)

    async with client:
        resp = await client.post(f"{BASE_URL}/pages", headers=headers, json=payload)
        resp.raise_for_status()
        return NotionPage.from_api(resp.json())


async def append_blocks(page_id: str, content: str) -> list[dict[str, Any]]:
    """Append content blocks to an existing page.

    Args:
        page_id: The page ID to append to
        content: Markdown content to append

    Returns:
        List of created block objects

    Example:
        await append_blocks("page-id", "## New Section\\n\\nMore content here.")
    """
    client, headers = await _get_client()
    blocks = _markdown_to_blocks(content)

    async with client:
        resp = await client.patch(
            f"{BASE_URL}/blocks/{page_id}/children",
            headers=headers,
            json={"children": blocks},
        )
        resp.raise_for_status()
        return resp.json().get("results", [])


async def update_page(
    page_id: str,
    properties: dict[str, Any] | None = None,
    archived: bool | None = None,
) -> NotionPage:
    """Update page properties.

    Args:
        page_id: The page ID to update
        properties: Properties to update
        archived: Set to True to archive the page

    Returns:
        Updated NotionPage object

    Example:
        # Update status
        await update_page("page-id", properties={
            "Status": {"status": {"name": "Done"}}
        })
        
        # Archive page
        await update_page("page-id", archived=True)
    """
    client, headers = await _get_client()

    payload: dict[str, Any] = {}
    if properties:
        payload["properties"] = properties
    if archived is not None:
        payload["archived"] = archived

    async with client:
        resp = await client.patch(
            f"{BASE_URL}/pages/{page_id}",
            headers=headers,
            json=payload,
        )
        resp.raise_for_status()
        return NotionPage.from_api(resp.json())


def extract_plain_text(blocks: list[dict[str, Any]]) -> str:
    """Extract plain text from Notion blocks.

    Args:
        blocks: List of Notion block objects

    Returns:
        Plain text content
    """
    text_parts = []
    
    for block in blocks:
        block_type = block.get("type", "")
        block_data = block.get(block_type, {})
        
        # Extract rich_text content
        rich_text = block_data.get("rich_text", [])
        if rich_text:
            text = "".join(rt.get("plain_text", "") for rt in rich_text)
            
            # Add formatting based on block type
            if block_type == "heading_1":
                text = f"# {text}"
            elif block_type == "heading_2":
                text = f"## {text}"
            elif block_type == "heading_3":
                text = f"### {text}"
            elif block_type == "bulleted_list_item":
                text = f"- {text}"
            elif block_type == "numbered_list_item":
                text = f"1. {text}"
            elif block_type == "code":
                lang = block_data.get("language", "")
                text = f"```{lang}\n{text}\n```"
            
            text_parts.append(text)
    
    return "\n".join(text_parts)


# =============================================================================
# CLI Interface
# =============================================================================


def _print_results(results: list[NotionPage | NotionDatabase]) -> None:
    """Print search results."""
    for i, r in enumerate(results, 1):
        if isinstance(r, NotionPage):
            print(f"{i}. [Page] {r.title}")
            print(f"   ID: {r.id}")
            if r.url:
                print(f"   URL: {r.url}")
        else:
            print(f"{i}. [Database] {r.title}")
            print(f"   ID: {r.id}")
            if r.description:
                print(f"   Description: {r.description}")
        print()


async def _cli_main() -> None:
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Notion API integration")
    subparsers = parser.add_subparsers(dest="command", help="Command")

    # search command
    search_p = subparsers.add_parser("search", help="Search pages and databases")
    search_p.add_argument("query", nargs="?", default="", help="Search query")
    search_p.add_argument("-t", "--type", choices=["page", "database"], help="Filter by type")
    search_p.add_argument("-n", "--limit", type=int, default=10, help="Max results")

    # page command
    page_p = subparsers.add_parser("page", help="Get page content")
    page_p.add_argument("id", help="Page ID")
    page_p.add_argument("--no-content", action="store_true", help="Skip content blocks")

    # database command
    db_p = subparsers.add_parser("database", help="Get database info")
    db_p.add_argument("id", help="Database ID")

    # query command
    query_p = subparsers.add_parser("query", help="Query database")
    query_p.add_argument("database_id", help="Database ID")
    query_p.add_argument("-n", "--limit", type=int, default=10, help="Max results")

    # create command
    create_p = subparsers.add_parser("create", help="Create a page")
    create_p.add_argument("parent_id", help="Parent database or page ID")
    create_p.add_argument("title", help="Page title")
    create_p.add_argument("-c", "--content", help="Page content (markdown)")
    create_p.add_argument("--page-parent", action="store_true", help="Parent is a page (not database)")

    args = parser.parse_args()

    if args.command == "search":
        results = await search(args.query, filter_type=args.type, page_size=args.limit)
        _print_results(results)

    elif args.command == "page":
        page = await get_page(args.id, include_content=not args.no_content)
        if page:
            print(f"Title: {page.title}")
            print(f"ID: {page.id}")
            print(f"URL: {page.url}")
            print(f"Created: {page.created_time}")
            print(f"Last edited: {page.last_edited_time}")
            if page.content_blocks:
                print(f"\nContent:\n{extract_plain_text(page.content_blocks)}")
        else:
            print("Page not found")

    elif args.command == "database":
        db = await get_database(args.id)
        if db:
            print(f"Title: {db.title}")
            print(f"ID: {db.id}")
            print(f"URL: {db.url}")
            if db.description:
                print(f"Description: {db.description}")
            print(f"\nProperties:")
            for name, schema in db.properties_schema.items():
                print(f"  - {name}: {schema.get('type', 'unknown')}")
        else:
            print("Database not found")

    elif args.command == "query":
        rows = await query_database(args.database_id, page_size=args.limit)
        print(f"Found {len(rows)} rows:\n")
        for row in rows:
            print(f"  - {row.title} ({row.id[:8]}...)")

    elif args.command == "create":
        parent_type = "page_id" if args.page_parent else "database_id"
        page = await create_page(
            args.parent_id,
            args.title,
            content=args.content,
            parent_type=parent_type,
        )
        print(f"Created page: {page.title}")
        print(f"ID: {page.id}")
        print(f"URL: {page.url}")

    else:
        parser.print_help()


if __name__ == "__main__":
    asyncio.run(_cli_main())
