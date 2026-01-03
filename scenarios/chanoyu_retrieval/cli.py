#!/usr/bin/env python3
"""CLI interface for the chanoyu retrieval tool.

Commands:
    search  - Find sources about a concept or person
    context - Get files to load for a research task
    sources - List all indexed sources
"""

import json
import sys
from pathlib import Path

import click

# Default paths
CHANOYU_ROOT = Path.home() / "switchboard/chanoyu"
INDEX_PATH = CHANOYU_ROOT / "_concept-source-index.json"


def load_index() -> dict:
    """Load the concept-source index."""
    if not INDEX_PATH.exists():
        click.echo(f"Error: Index not found at {INDEX_PATH}", err=True)
        click.echo("Run the index builder first.", err=True)
        sys.exit(1)

    with open(INDEX_PATH) as f:
        return json.load(f)


@click.group()
@click.version_option(version="0.1.0")
def main():
    """Chanoyu Retrieval Tool - Find sources and context for tea ceremony research.

    Search the indexed sources for concepts, people, and research context.

    Examples:

        chanoyu search wabi
        chanoyu search rikyu --type person
        chanoyu context "raku ware techniques"
        chanoyu sources
    """
    pass


@main.command()
@click.argument("query")
@click.option(
    "--type",
    "search_type",
    type=click.Choice(["concept", "person", "auto"]),
    default="auto",
    help="Search type: concept, person, or auto-detect (default)",
)
@click.option("--verbose", "-v", is_flag=True, help="Show detailed source information")
def search(query: str, search_type: str, verbose: bool):
    """Search for sources about a concept or person.

    QUERY is the concept or person name to search for.

    Examples:

        chanoyu search wabi
        chanoyu search "korean tea bowls"
        chanoyu search rikyu --type person
    """
    index = load_index()
    query_lower = query.lower().replace(" ", "-")

    results = []

    # Auto-detect or explicit search
    if search_type in ("concept", "auto"):
        if query_lower in index.get("concepts", {}):
            concept_data = index["concepts"][query_lower]
            for source in concept_data.get("sources", []):
                source_id = source["id"]
                source_meta = index["sources"].get(source_id, {})
                results.append({
                    "match_type": "concept",
                    "query": query_lower,
                    "relevance": source["relevance"],
                    "source_id": source_id,
                    "title": source_meta.get("title", source_id),
                    "japanese": source_meta.get("japanese", ""),
                    "author": source_meta.get("author", ""),
                    "year": source_meta.get("year", ""),
                    "path": source_meta.get("path", ""),
                    "has_learnings": source_meta.get("has_learnings", False),
                })

    if search_type in ("person", "auto"):
        if query_lower in index.get("people", {}):
            person_data = index["people"][query_lower]
            for source_id in person_data.get("sources", []):
                source_meta = index["sources"].get(source_id, {})
                # Check if already in results
                if not any(r["source_id"] == source_id for r in results):
                    results.append({
                        "match_type": "person",
                        "query": query_lower,
                        "relevance": "mentioned",
                        "source_id": source_id,
                        "title": source_meta.get("title", source_id),
                        "japanese": source_meta.get("japanese", ""),
                        "author": source_meta.get("author", ""),
                        "year": source_meta.get("year", ""),
                        "path": source_meta.get("path", ""),
                        "has_learnings": source_meta.get("has_learnings", False),
                    })

    if not results:
        click.echo(f"No sources found for '{query}'")
        click.echo("\nTry:")
        click.echo("  • A different spelling (e.g., 'wabi' not 'wabi-sabi')")
        click.echo("  • Checking available concepts: chanoyu sources --concepts")
        return

    # Sort by relevance (primary first) then year
    relevance_order = {"primary": 0, "supporting": 1, "mentioned": 2}
    results.sort(key=lambda r: (relevance_order.get(r["relevance"], 3), r.get("year", 9999)))

    click.echo(f"\n Found {len(results)} source(s) for '{query}':\n")

    for r in results:
        relevance_badge = {
            "primary": "[PRIMARY]",
            "supporting": "[supporting]",
            "mentioned": "[mentioned]",
        }.get(r["relevance"], "")

        learnings_badge = " [learnings]" if r["has_learnings"] else ""

        click.echo(f"  {relevance_badge} {r['title']} ({r['year']}){learnings_badge}")

        if verbose:
            if r["japanese"]:
                click.echo(f"           {r['japanese']}")
            click.echo(f"           Author: {r['author']}")
            click.echo(f"           Path: {CHANOYU_ROOT / r['path']}")
            if r["has_learnings"]:
                click.echo(f"           Learnings: {CHANOYU_ROOT / r['path']}/_learnings.md")
            click.echo()


@main.command()
@click.argument("topic")
@click.option("--max-files", "-n", default=5, help="Maximum files to suggest (default: 5)")
def context(topic: str, max_files: int):
    """Get files to load for a research task.

    TOPIC is the research topic or task description.

    Examples:

        chanoyu context "writing about raku ware"
        chanoyu context "letter for robiraki"
        chanoyu context "understanding wabi aesthetic"
    """
    index = load_index()
    topic_lower = topic.lower()

    # Simple keyword matching (future: AI semantic matching)
    matches = []

    # Check concepts
    for concept, data in index.get("concepts", {}).items():
        if concept in topic_lower or topic_lower in concept:
            for source in data.get("sources", []):
                source_id = source["id"]
                source_meta = index["sources"].get(source_id, {})
                if source_meta.get("has_learnings"):
                    path = CHANOYU_ROOT / source_meta["path"] / "_learnings.md"
                    if path not in [m["path"] for m in matches]:
                        matches.append({
                            "path": path,
                            "reason": f"covers '{concept}'",
                            "relevance": source["relevance"],
                            "title": source_meta.get("title", source_id),
                        })

    # Check people
    for person, data in index.get("people", {}).items():
        if person in topic_lower or topic_lower in person:
            for source_id in data.get("sources", []):
                source_meta = index["sources"].get(source_id, {})
                if source_meta.get("has_learnings"):
                    path = CHANOYU_ROOT / source_meta["path"] / "_learnings.md"
                    if path not in [m["path"] for m in matches]:
                        matches.append({
                            "path": path,
                            "reason": f"mentions '{person}'",
                            "relevance": "mentioned",
                            "title": source_meta.get("title", source_id),
                        })

    # Sort by relevance
    relevance_order = {"primary": 0, "supporting": 1, "mentioned": 2}
    matches.sort(key=lambda m: relevance_order.get(m["relevance"], 3))

    if not matches:
        click.echo(f"No context files found for '{topic}'")
        click.echo("\nTry:")
        click.echo("  • More specific keywords (e.g., 'wabi' 'rikyu' 'raku')")
        click.echo("  • Checking indexed concepts: chanoyu sources --concepts")
        return

    # Limit results
    matches = matches[:max_files]

    click.echo(f"\n Context files for '{topic}':\n")
    click.echo("Load these files for relevant context:\n")

    for m in matches:
        click.echo(f"  • {m['path']}")
        click.echo(f"    ({m['title']} - {m['reason']})\n")

    # Output copyable paths
    click.echo("\n--- Copy-paste paths ---")
    for m in matches:
        click.echo(str(m["path"]))


@main.command()
@click.option("--concepts", is_flag=True, help="List all indexed concepts")
@click.option("--people", is_flag=True, help="List all indexed people")
@click.option("--verbose", "-v", is_flag=True, help="Show detailed information")
def sources(concepts: bool, people: bool, verbose: bool):
    """List all indexed sources.

    Examples:

        chanoyu sources
        chanoyu sources --concepts
        chanoyu sources --people
    """
    index = load_index()

    if concepts:
        click.echo("\n Indexed Concepts:\n")
        for concept in sorted(index.get("concepts", {}).keys()):
            data = index["concepts"][concept]
            source_count = len(data.get("sources", []))
            click.echo(f"  • {concept} ({source_count} source{'s' if source_count != 1 else ''})")
        return

    if people:
        click.echo("\n Indexed People:\n")
        for person in sorted(index.get("people", {}).keys()):
            data = index["people"][person]
            source_count = len(data.get("sources", []))
            click.echo(f"  • {person} ({source_count} source{'s' if source_count != 1 else ''})")
        return

    # Default: list sources
    click.echo("\n Indexed Sources:\n")
    for source_id, meta in sorted(index.get("sources", {}).items(), key=lambda x: x[1].get("year", 0)):
        learnings_badge = " [learnings]" if meta.get("has_learnings") else ""
        click.echo(f"  {meta.get('year', '????')} | {meta.get('title', source_id)}{learnings_badge}")

        if verbose:
            if meta.get("japanese"):
                click.echo(f"         {meta['japanese']}")
            click.echo(f"         Author: {meta.get('author', 'Unknown')}")
            click.echo(f"         Concepts: {', '.join(meta.get('concepts', []))}")
            click.echo(f"         People: {', '.join(meta.get('people', []))}")
            click.echo()

    # Summary
    total = len(index.get("sources", {}))
    with_learnings = sum(1 for s in index.get("sources", {}).values() if s.get("has_learnings"))
    click.echo(f"\n  Total: {total} sources ({with_learnings} with extracted learnings)")


if __name__ == "__main__":
    main()
