"""Academic paper search using Semantic Scholar API.

Native Amplifier skill that integrates with the secrets management system.
Works everywhere: main session, subagents, SDK, scripts, cron jobs.

Usage:
    from amplifier.skills.academic_search import search_papers, search_author

    # Search for papers
    papers = await search_papers("Sen no Rikyu tea ceremony")
    
    # Search by author
    papers = await search_author("Vikash Mansinghka", topic="probabilistic programming")
    
    # Get paper details
    details = await get_paper("10.1145/3453483.3454077")  # DOI or paper ID
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any

import httpx

from amplifier.utils.secrets import get_semantic_scholar_api_key

# API Configuration
BASE_URL = "https://api.semanticscholar.org/graph/v1"
DEFAULT_FIELDS = "title,authors,year,abstract,citationCount,url,externalIds"
DETAILED_FIELDS = "title,authors,year,abstract,citationCount,url,externalIds,venue,publicationDate,references,citations"


@dataclass
class Paper:
    """Represents an academic paper."""

    paper_id: str
    title: str
    authors: list[str]
    year: int | None
    abstract: str | None
    citation_count: int
    url: str | None
    doi: str | None

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> Paper:
        """Create Paper from Semantic Scholar API response."""
        authors = [a.get("name", "Unknown") for a in data.get("authors", [])]
        external_ids = data.get("externalIds", {}) or {}
        return cls(
            paper_id=data.get("paperId", ""),
            title=data.get("title", "Untitled"),
            authors=authors,
            year=data.get("year"),
            abstract=data.get("abstract"),
            citation_count=data.get("citationCount", 0),
            url=data.get("url"),
            doi=external_ids.get("DOI"),
        )

    def __str__(self) -> str:
        authors_str = ", ".join(self.authors[:3])
        if len(self.authors) > 3:
            authors_str += f" +{len(self.authors) - 3} more"
        return f"{self.title} ({self.year or '?'}) - {authors_str} [{self.citation_count} citations]"


async def _get_client() -> tuple[httpx.AsyncClient, dict[str, str]]:
    """Get HTTP client with authentication headers."""
    try:
        api_key = get_semantic_scholar_api_key()
        headers = {"x-api-key": api_key}
    except RuntimeError:
        # Fall back to unauthenticated (rate limited to ~5-10 req/min)
        headers = {}
    return httpx.AsyncClient(timeout=30), headers


async def search_papers(
    query: str,
    limit: int = 10,
    year_range: tuple[int, int] | None = None,
    fields: str = DEFAULT_FIELDS,
) -> list[Paper]:
    """Search for academic papers.

    Args:
        query: Search query (title, topic, keywords)
        limit: Maximum number of results (default 10, max 100)
        year_range: Optional (start_year, end_year) tuple to filter results
        fields: API fields to retrieve

    Returns:
        List of Paper objects

    Example:
        papers = await search_papers("transformer attention mechanism", limit=5)
        for p in papers:
            print(p)
    """
    client, headers = await _get_client()

    params: dict[str, Any] = {
        "query": query,
        "limit": min(limit, 100),
        "fields": fields,
    }

    if year_range:
        params["year"] = f"{year_range[0]}-{year_range[1]}"

    async with client:
        resp = await client.get(f"{BASE_URL}/paper/search", params=params, headers=headers)
        resp.raise_for_status()
        data = resp.json()

    return [Paper.from_api(p) for p in data.get("data", [])]


async def search_author(
    author_name: str,
    topic: str | None = None,
    limit: int = 10,
) -> list[Paper]:
    """Search for papers by a specific author.

    Args:
        author_name: Author name to search for
        topic: Optional topic to filter results
        limit: Maximum number of results

    Returns:
        List of Paper objects

    Example:
        papers = await search_author("Geoffrey Hinton", topic="deep learning")
    """
    query = f'author:"{author_name}"'
    if topic:
        query += f" {topic}"
    return await search_papers(query, limit=limit)


async def get_paper(paper_id: str, include_references: bool = False) -> Paper | None:
    """Get detailed information about a specific paper.

    Args:
        paper_id: Semantic Scholar paper ID, DOI, or arXiv ID
            - DOI: "10.1145/3453483.3454077" or "DOI:10.1145/..."
            - arXiv: "arXiv:2103.14030"
            - S2 ID: "649def34f8be52c8b66281af98ae884c09aef38b"
        include_references: Include references and citations (slower)

    Returns:
        Paper object or None if not found

    Example:
        paper = await get_paper("10.1145/3453483.3454077")
        print(paper.abstract)
    """
    client, headers = await _get_client()

    # Handle DOI format
    if "/" in paper_id and not paper_id.startswith("DOI:"):
        paper_id = f"DOI:{paper_id}"

    fields = DETAILED_FIELDS if include_references else DEFAULT_FIELDS

    async with client:
        try:
            resp = await client.get(
                f"{BASE_URL}/paper/{paper_id}",
                params={"fields": fields},
                headers=headers,
            )
            resp.raise_for_status()
            return Paper.from_api(resp.json())
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return None
            raise


async def search_recent(
    topic: str,
    years_back: int = 2,
    limit: int = 10,
    min_citations: int = 0,
) -> list[Paper]:
    """Search for recent papers on a topic.

    Args:
        topic: Research topic to search
        years_back: How many years back to search (default 2)
        limit: Maximum results
        min_citations: Minimum citation count filter

    Returns:
        List of Paper objects, sorted by citation count

    Example:
        papers = await search_recent("large language models", years_back=1)
    """
    from datetime import datetime

    current_year = datetime.now().year
    start_year = current_year - years_back

    papers = await search_papers(topic, limit=limit * 2, year_range=(start_year, current_year))

    # Filter by citation count and sort
    filtered = [p for p in papers if p.citation_count >= min_citations]
    filtered.sort(key=lambda p: p.citation_count, reverse=True)

    return filtered[:limit]


# =============================================================================
# CLI Interface
# =============================================================================


def _print_papers(papers: list[Paper], verbose: bool = False) -> None:
    """Print papers in a readable format."""
    for i, p in enumerate(papers, 1):
        print(f"\n{i}. {p.title} ({p.year or '?'})")
        authors = ", ".join(p.authors[:3])
        if len(p.authors) > 3:
            authors += f" +{len(p.authors) - 3} more"
        print(f"   Authors: {authors}")
        print(f"   Citations: {p.citation_count}")
        if p.doi:
            print(f"   DOI: {p.doi}")
        if verbose and p.abstract:
            abstract = p.abstract[:200] + "..." if len(p.abstract) > 200 else p.abstract
            print(f"   Abstract: {abstract}")


async def _cli_main() -> None:
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Search academic papers via Semantic Scholar")
    subparsers = parser.add_subparsers(dest="command", help="Command")

    # search command
    search_p = subparsers.add_parser("search", help="Search for papers")
    search_p.add_argument("query", help="Search query")
    search_p.add_argument("-n", "--limit", type=int, default=10, help="Max results")
    search_p.add_argument("-v", "--verbose", action="store_true", help="Show abstracts")
    search_p.add_argument("--year-from", type=int, help="Start year filter")
    search_p.add_argument("--year-to", type=int, help="End year filter")

    # author command
    author_p = subparsers.add_parser("author", help="Search by author")
    author_p.add_argument("name", help="Author name")
    author_p.add_argument("-t", "--topic", help="Filter by topic")
    author_p.add_argument("-n", "--limit", type=int, default=10, help="Max results")
    author_p.add_argument("-v", "--verbose", action="store_true", help="Show abstracts")

    # paper command
    paper_p = subparsers.add_parser("paper", help="Get paper details")
    paper_p.add_argument("id", help="Paper ID, DOI, or arXiv ID")

    # recent command
    recent_p = subparsers.add_parser("recent", help="Search recent papers")
    recent_p.add_argument("topic", help="Research topic")
    recent_p.add_argument("-y", "--years", type=int, default=2, help="Years back")
    recent_p.add_argument("-n", "--limit", type=int, default=10, help="Max results")
    recent_p.add_argument("-c", "--min-citations", type=int, default=0, help="Min citations")
    recent_p.add_argument("-v", "--verbose", action="store_true", help="Show abstracts")

    args = parser.parse_args()

    if args.command == "search":
        year_range = None
        if args.year_from or args.year_to:
            year_range = (args.year_from or 1900, args.year_to or 2100)
        papers = await search_papers(args.query, limit=args.limit, year_range=year_range)
        _print_papers(papers, args.verbose)

    elif args.command == "author":
        papers = await search_author(args.name, topic=args.topic, limit=args.limit)
        _print_papers(papers, args.verbose)

    elif args.command == "paper":
        paper = await get_paper(args.id)
        if paper:
            print(f"\nTitle: {paper.title}")
            print(f"Authors: {', '.join(paper.authors)}")
            print(f"Year: {paper.year}")
            print(f"Citations: {paper.citation_count}")
            if paper.doi:
                print(f"DOI: {paper.doi}")
            if paper.url:
                print(f"URL: {paper.url}")
            if paper.abstract:
                print(f"\nAbstract:\n{paper.abstract}")
        else:
            print("Paper not found")

    elif args.command == "recent":
        papers = await search_recent(
            args.topic,
            years_back=args.years,
            limit=args.limit,
            min_citations=args.min_citations,
        )
        _print_papers(papers, args.verbose)

    else:
        parser.print_help()


if __name__ == "__main__":
    asyncio.run(_cli_main())
