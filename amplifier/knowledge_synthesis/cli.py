"""
Command-line interface for knowledge synthesis.
Simple, direct commands for extracting knowledge from content files.
"""

import asyncio
import json
import logging
import os
from typing import Any

import click

from amplifier.config.paths import paths
from amplifier.knowledge_integration import UnifiedKnowledgeExtractor
from amplifier.utils.notifications import send_notification

from .domain_config import list_available_domains
from .domain_config import load_domain_config
from .events import EventEmitter
from .store import KnowledgeStore

# Set up logging
logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)


@click.group()
def cli():
    """Knowledge synthesis from content files."""
    pass


@cli.command()
@click.option(
    "--max-items",
    default=None,
    type=int,
    help="Maximum number of content items to process (default: all)",
)
@click.option(
    "--resilient/--no-resilient",
    default=True,
    help="Use resilient mining with partial failure handling (default: True)",
)
@click.option(
    "--skip-partial-failures",
    is_flag=True,
    default=False,
    help="Skip articles with partial failures instead of retrying them (default: retry partials)",
)
@click.option(
    "--notify",
    is_flag=True,
    default=False,
    help="Send desktop notifications on completion",
)
@click.option(
    "--domains",
    default=None,
    help="Comma-separated domain IDs (e.g., 'chanoyu,poa'). Use 'list' to see available domains.",
)
def sync(max_items: int | None, resilient: bool, skip_partial_failures: bool, notify: bool, domains: str | None):
    """
    Sync and extract knowledge from content files.

    Scans all configured content directories for content files and extracts
    concepts, relationships, insights, and patterns.

    With --resilient (default), uses partial failure handling to continue
    processing even when individual processors fail.

    By default, retries articles with partial failures. Use --skip-partial-failures
    to process only new articles.

    Use --domains to specify which knowledge domains to extract for.
    This customizes the extraction prompts with domain-specific context.
    """
    # By default, retry partial failures unless skip flag is set
    retry_partial_mode = not skip_partial_failures

    # Handle --domains list command
    if domains == "list":
        available = list_available_domains()
        if available:
            logger.info("Available domains:")
            for domain_id in available:
                config = load_domain_config(domain_id)
                domain_name = config.get("domain", {}).get("name", domain_id) if config else domain_id
                logger.info(f"  • {domain_id}: {domain_name}")
        else:
            logger.info("No domain configurations found.")
            logger.info("Add configs to ~/switchboard/{domain}/.extraction-config.yaml")
        return

    # Parse domain list
    domain_configs: list[dict[str, Any]] = []
    if domains:
        domain_ids = [d.strip() for d in domains.split(",")]
        for domain_id in domain_ids:
            config = load_domain_config(domain_id)
            if config:
                domain_configs.append(config)
                domain_name = config.get("domain", {}).get("name", domain_id)
                logger.info(f"Loaded domain config: {domain_name}")
            else:
                logger.warning(f"Domain config not found: {domain_id}")

    try:
        if resilient:
            asyncio.run(_sync_content_resilient(max_items, retry_partial_mode, notify, domain_configs))
        else:
            asyncio.run(_sync_content(max_items, notify, domain_configs))
    except KeyboardInterrupt:
        if notify:
            send_notification(
                title="Amplifier",
                message="Knowledge sync interrupted by user",
                cwd=os.getcwd(),
            )
        raise
    except Exception as e:
        if notify:
            send_notification(
                title="Amplifier",
                message=f"Knowledge sync failed: {str(e)[:100]}",
                cwd=os.getcwd(),
            )
        raise


async def _sync_content(
    max_items: int | None, notify: bool = False, domain_configs: list[dict[str, Any]] | None = None
):
    """Sync and extract knowledge from content files.

    Args:
        max_items: Maximum items to process
        notify: Whether to send notifications
        domain_configs: List of domain configurations for focused extraction
    """
    # Import the new content loader
    from amplifier.content_loader import ContentLoader

    # Initialize components
    synthesizer = UnifiedKnowledgeExtractor()
    store = KnowledgeStore()
    emitter = EventEmitter()
    loader = ContentLoader()

    # Load all content items (quiet mode to suppress progress output)
    content_items = list(loader.load_all(quiet=True))

    if not content_items:
        logger.info("No content files found in configured directories.")
        logger.info("Check AMPLIFIER_CONTENT_DIRS environment variable.")
        emitter.emit("sync_finished", stage="init", data={"processed": 0, "skipped": 0, "reason": "no_content"})
        return

    logger.info(f"Found {len(content_items)} content files")

    # Process content items
    processed = 0
    skipped = 0
    emitter.emit("sync_started", stage="sync", data={"total": len(content_items), "max": max_items})

    for item in content_items:
        # Check max items limit
        if max_items and processed >= max_items:
            break

        # Skip if already processed
        if store.is_processed(item.content_id):
            logger.info(f"✓ Already processed: {item.title}")
            skipped += 1
            emitter.emit(
                "content_skipped",
                stage="precheck",
                source_id=item.content_id,
                data={"title": item.title, "reason": "already_processed"},
            )
            continue

        # Extract knowledge
        logger.info(f"\nProcessing: {item.title}")
        logger.debug(f"  From: {item.source_path}")
        emitter.emit(
            "extraction_started",
            stage="extract",
            source_id=item.content_id,
            data={"title": item.title},
        )
        try:
            # Create a task for extraction with progress indicator
            extraction_task = asyncio.create_task(
                synthesizer.extract_from_text(
                    text=item.content,
                    title=item.title,
                    source=item.content_id,
                )
            )

            # Show progress while extraction is running
            dots = 0
            while not extraction_task.done():
                await asyncio.sleep(3)  # Check every 3 seconds
                if not extraction_task.done():
                    dots = (dots + 1) % 4
                    progress_msg = "  Extracting" + "." * (dots + 1) + " " * (3 - dots)
                    print(f"\r{progress_msg}", end="", flush=True)

            # Clear the progress line
            print("\r" + " " * 40 + "\r", end="", flush=True)

            # Get the result
            extraction_result = await extraction_task

            # Convert UnifiedExtraction to dict format expected by store
            extraction = {
                "source_id": item.content_id,
                "title": item.title,
                "concepts": extraction_result.concepts,  # Already a list of dicts
                "relationships": [
                    {"subject": r.subject, "predicate": r.predicate, "object": r.object, "confidence": r.confidence}
                    for r in extraction_result.relationships
                ],
                "insights": extraction_result.key_insights,  # Use key_insights field
                "patterns": extraction_result.code_patterns,  # Use code_patterns field
            }

            # Add metadata from ContentItem
            from pathlib import Path

            extraction["url"] = item.metadata.get("url", "")
            extraction["author"] = item.metadata.get("author", "")
            extraction["publication"] = item.metadata.get("publication", "")
            extraction["content_dir"] = str(Path(item.source_path).parent)  # Track source directory

            # Save extraction
            store.save(extraction)

            # Report results
            logger.info(
                f"  → Extracted: {len(extraction.get('concepts', []))} concepts, "
                f"{len(extraction.get('relationships', []))} relationships, "
                f"{len(extraction.get('insights', []))} insights"
            )
            processed += 1
            emitter.emit(
                "extraction_succeeded",
                stage="extract",
                source_id=item.content_id,
                data={
                    "title": item.title,
                    "concepts": len(extraction.get("concepts", [])),
                    "relationships": len(extraction.get("relationships", [])),
                    "insights": len(extraction.get("insights", [])),
                },
            )

        except KeyboardInterrupt:
            logger.info("\n⚠ Interrupted - saving progress...")
            if notify:
                send_notification(
                    title="Amplifier",
                    message=f"Sync interrupted. Processed {processed} items",
                    cwd=os.getcwd(),
                )
            break
        except Exception as e:
            logger.error(f"\n{'=' * 60}")
            logger.error(f"FATAL: Extraction failed for {item.content_id}")
            logger.error(f"Error: {e}")
            logger.error(f"{'=' * 60}")
            emitter.emit(
                "extraction_failed",
                stage="extract",
                source_id=item.content_id,
                data={"title": item.title, "error": str(e)},
            )
            raise  # Stop immediately on extraction failure

    # Summary
    logger.info(f"\n{'=' * 50}")
    logger.info(f"Processed: {processed} items")
    logger.info(f"Skipped (already done): {skipped}")
    logger.info(f"Total extractions: {store.count()}")

    # Show error summary
    error_summary = store.get_error_summary()
    logger.info(f"Extraction quality: {error_summary}")

    emitter.emit(
        "sync_finished",
        stage="sync",
        data={"processed": processed, "skipped": skipped, "total": len(content_items)},
    )

    # Send completion notification
    if notify:
        send_notification(
            title="Amplifier",
            message=f"Knowledge sync complete: {processed} items processed, {skipped} skipped",
            cwd=os.getcwd(),
        )


async def _sync_content_resilient(
    max_items: int | None,
    retry_partial: bool = False,
    notify: bool = False,
    domain_configs: list[dict[str, Any]] | None = None,
):
    """Sync content with resilient partial failure handling.

    Args:
        max_items: Maximum items to process
        retry_partial: Whether to retry partial failures
        notify: Whether to send notifications
        domain_configs: List of domain configurations for focused extraction
    """
    from amplifier.content_loader import ContentLoader

    from .article_processor import ArticleProcessor

    # Initialize components with domain configs
    miner = ArticleProcessor(domain_configs=domain_configs)
    loader = ContentLoader()
    emitter = EventEmitter()

    # Load all content items (quiet mode to suppress progress output)
    content_items = list(loader.load_all(quiet=True))

    if not content_items:
        logger.info("No content files found in configured directories.")
        logger.info("Check AMPLIFIER_CONTENT_DIRS environment variable.")
        emitter.emit("sync_finished", stage="init", data={"processed": 0, "skipped": 0, "reason": "no_content"})
        return

    logger.info(f"Found {len(content_items)} content files")

    # Pre-scan to count existing status
    already_complete = 0
    already_partial = 0
    to_process = 0

    for item in content_items:
        existing_status = miner.status_store.load_status(item.content_id)
        if existing_status:
            if existing_status.is_complete:
                already_complete += 1
            else:
                already_partial += 1
                if retry_partial:
                    to_process += 1
        else:
            to_process += 1

    # Show summary
    logger.info("\nProcessing Summary:")
    logger.info(f"  Already complete: {already_complete}")
    logger.info(f"  Partial results: {already_partial}")
    logger.info(f"  To process: {to_process}")
    if retry_partial and already_partial > 0:
        logger.info(f"  ✓ Including {already_partial} articles with partial failures (default behavior)")
    elif not retry_partial and already_partial > 0:
        logger.info(f"  ⚠ Skipping {already_partial} articles with partial failures (--skip-partial-failures)")
    logger.info("")

    # Process with resilient miner
    processed = 0
    failed = 0
    partial = 0

    emitter.emit("sync_started", stage="sync", data={"total": len(content_items), "max": max_items})

    for idx, item in enumerate(content_items):
        # Check max items limit
        if max_items and processed >= max_items:
            break

        # Check if already processed
        existing_status = miner.status_store.load_status(item.content_id)
        if existing_status:
            if existing_status.is_complete:
                logger.info(f"✓ Already complete: {item.title}")
                processed += 1
                continue
            if not retry_partial:
                # Has partial results but skip-partial-failures flag is set
                successful_count = sum(
                    1 for r in existing_status.processor_results.values() if r.status in ["success", "empty"]
                )
                if successful_count > 0:
                    logger.info(
                        f"⚠ Skipping partial (--skip-partial-failures): {item.title} ({successful_count}/4 processors succeeded)"
                    )
                    partial += 1
                    continue

        # Process article with resilient handling
        try:
            # Process with resilient miner (directly pass ContentItem)
            status = await miner.process_article_with_logging(item, current=idx + 1, total=len(content_items))

            # Update counters based on status
            if status.is_complete:
                processed += 1
            else:
                # Check if we got partial results
                successful_processors = [
                    name for name, result in status.processor_results.items() if result.status in ["success", "empty"]
                ]
                if successful_processors:
                    partial += 1
                else:
                    failed += 1

            # Emit appropriate event
            emitter.emit(
                "extraction_completed",
                stage="extract",
                source_id=item.content_id,
                data={
                    "title": item.title,
                    "complete": status.is_complete,
                    "processors": {name: result.status for name, result in status.processor_results.items()},
                },
            )

        except KeyboardInterrupt:
            logger.info("\n⚠ Interrupted - saving progress...")
            if notify:
                send_notification(
                    title="Amplifier",
                    message=f"Sync interrupted. Processed {processed}, partial {partial}, failed {failed}",
                    cwd=os.getcwd(),
                )
            break
        except Exception as e:
            logger.error(f"  ✗ Unexpected error: {e}")
            failed += 1
            emitter.emit(
                "extraction_failed",
                stage="extract",
                source_id=item.content_id,
                data={"title": item.title, "error": str(e)},
            )

    # Generate and display comprehensive report
    logger.info(f"\n{'=' * 60}")
    logger.info("PROCESSING COMPLETE - SUMMARY REPORT")
    logger.info(f"{'=' * 60}")

    # Get report from miner
    report_data = miner.get_processing_report()

    # Display summary from report
    if report_data:
        summary_data = report_data.get("summary", {})
        logger.info("\nProcessing Summary:")
        logger.info(f"  Total Articles: {summary_data.get('total_articles', 0)}")
        logger.info(f"  Complete: {summary_data.get('complete', 0)}")
        logger.info(f"  Partial: {summary_data.get('partial', 0)}")
        logger.info(f"  Failed: {summary_data.get('failed', 0)}")
        logger.info(f"  Needs Retry: {summary_data.get('needs_retry', 0)}")

        # Show extraction stats
        extraction_stats = report_data.get("extraction_stats", {})
        if extraction_stats:
            logger.info("\nExtraction Statistics:")
            logger.info(f"  Total Concepts: {extraction_stats.get('total_concepts', 0)}")
            logger.info(f"  Total Relationships: {extraction_stats.get('total_relationships', 0)}")
            logger.info(f"  Total Insights: {extraction_stats.get('total_insights', 0)}")
            logger.info(f"  Total Patterns: {extraction_stats.get('total_patterns', 0)}")

    # Basic stats
    logger.info("\nOverall Statistics:")
    logger.info(f"  Complete: {processed} articles (all processors succeeded)")
    logger.info(f"  Partial: {partial} articles (some processors failed)")
    logger.info(f"  Failed: {failed} articles (all processors failed)")
    logger.info(f"  Total processed: {processed + partial + failed}")

    # Emit completion event
    emitter.emit(
        "sync_finished",
        stage="sync",
        data={
            "processed": processed,
            "partial": partial,
            "failed": failed,
            "total": len(content_items),
        },
    )

    # Suggest next actions if there were failures
    if partial > 0 or failed > 0:
        logger.info(f"\n{'=' * 60}")
        logger.info("NEXT ACTIONS:")
        logger.info(f"{'=' * 60}")
        logger.info("1. Review the failures above to identify systematic issues")
        logger.info("2. Fix any configuration or service problems")
        logger.info("3. Run sync again to retry failed articles:")
        logger.info("   make knowledge-sync")
        logger.info("4. View statistics and details:")
        logger.info("   make knowledge-stats")

    # Send completion notification with results
    if notify:
        if partial > 0 or failed > 0:
            # Had some failures - user action needed
            send_notification(
                title="Amplifier",
                message=f"Action needed: {processed} complete, {partial} partial, {failed} failed",
                cwd=os.getcwd(),
            )
        else:
            # All successful
            send_notification(
                title="Amplifier",
                message=f"Knowledge sync complete: {processed} articles successfully processed",
                cwd=os.getcwd(),
            )


@cli.command()
@click.option("--n", "n", default=50, type=int, help="Number of events to show")
@click.option("--event", "event_filter", default=None, type=str, help="Filter by event type")
@click.option("--follow/--no-follow", default=False, help="Follow events (like tail -f)")
def events(n: int, event_filter: str | None, follow: bool) -> None:
    """Show or follow pipeline events."""
    path = paths.data_dir / "knowledge" / "events.jsonl"
    emitter = EventEmitter(path)

    import time as _time

    if not path.exists():
        logger.info(f"No events found at {path}")
        return

    def _print_once() -> None:
        rows = emitter.tail(n=n, event_filter=event_filter)
        if not rows:
            logger.info("No matching events")
            return
        for ev in rows:
            ts = _time.strftime("%Y-%m-%d %H:%M:%S", _time.localtime(ev.timestamp))
            src = f" [{ev.source_id}]" if ev.source_id else ""
            details = ""
            if ev.data:
                # Compact one-line detail
                try:
                    details = " " + json.dumps(ev.data, ensure_ascii=False)
                except Exception:
                    details = ""
            print(f"{ts} - {ev.event}{src}{details}")

    _print_once()
    if follow:
        # Simple follow: print new lines as they arrive
        last_size = path.stat().st_size
        try:
            while True:
                _time.sleep(1)
                new_size = path.stat().st_size
                if new_size > last_size:
                    # Read newly appended lines
                    with open(path, encoding="utf-8") as f:
                        f.seek(last_size)
                        for line in f:
                            try:
                                obj = json.loads(line)
                            except json.JSONDecodeError:
                                continue
                            if event_filter and obj.get("event") != event_filter:
                                continue
                            ts = _time.strftime("%Y-%m-%d %H:%M:%S", _time.localtime(float(obj.get("timestamp", 0.0))))
                            src = f" [{obj.get('source_id')}]" if obj.get("source_id") else ""
                            data = obj.get("data")
                            details = ""
                            if data is not None:
                                try:
                                    details = " " + json.dumps(data, ensure_ascii=False)
                                except Exception:
                                    details = ""
                            print(f"{ts} - {obj.get('event')}{src}{details}")
                    last_size = new_size
        except KeyboardInterrupt:
            return


@cli.command("events-summary")
@click.option(
    "--scope",
    type=click.Choice(["last", "all"], case_sensitive=False),
    default="last",
    help="Summarize last run (default) or all events",
)
def events_summary(scope: str) -> None:
    """Summarize pipeline events."""
    path = paths.data_dir / "knowledge" / "events.jsonl"
    if not path.exists():
        logger.info(f"No events found at {path}")
        return

    # Load events
    rows: list[dict[str, Any]] = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue

    if not rows:
        logger.info("No events to summarize")
        return

    # Determine window
    start_idx = 0
    end_idx = len(rows) - 1
    if scope.lower() == "last":
        # Find last sync_finished, then back to the preceding sync_started
        last_finish = None
        for i in range(len(rows) - 1, -1, -1):
            if rows[i].get("event") == "sync_finished":
                last_finish = i
                break
        if last_finish is None:
            # No completed runs; take from last sync_started if any
            for i in range(len(rows) - 1, -1, -1):
                if rows[i].get("event") == "sync_started":
                    start_idx = i
                    break
            end_idx = len(rows) - 1
        else:
            end_idx = last_finish
            start_idx = 0
            for i in range(last_finish, -1, -1):
                if rows[i].get("event") == "sync_started":
                    start_idx = i
                    break

    window = rows[start_idx : end_idx + 1]
    if not window:
        logger.info("No events in selected window")
        return

    # Aggregate
    from collections import Counter

    by_type: Counter[str] = Counter(ev.get("event", "") for ev in window)
    skipped_reasons: Counter[str] = Counter(
        (ev.get("data", {}) or {}).get("reason", "") for ev in window if ev.get("event") == "content_skipped"
    )
    success = by_type.get("extraction_succeeded", 0)
    failures = by_type.get("extraction_failed", 0)
    started = by_type.get("extraction_started", 0)

    # Duration
    started_ts = next((ev.get("timestamp") for ev in window if ev.get("event") == "sync_started"), None)
    finished_ts = next((ev.get("timestamp") for ev in reversed(window) if ev.get("event") == "sync_finished"), None)
    duration_s = (float(finished_ts) - float(started_ts)) if started_ts and finished_ts else None

    # Processed/skipped totals from summary if present
    processed = None
    skipped = None
    total = None
    for ev in reversed(window):
        if ev.get("event") == "sync_finished":
            data = ev.get("data", {}) or {}
            processed = data.get("processed")
            skipped = data.get("skipped")
            total = data.get("total")
            break

    # Print
    print("\n=== Event Summary ===")
    print(f"Scope: {'last run' if scope.lower() == 'last' else 'all events'}")
    if duration_s is not None:
        print(f"Duration: {duration_s:.1f}s")
    if processed is not None:
        print(f"Processed: {processed}  Skipped: {skipped}  Total: {total}")
    print(f"Starts: {started}  Success: {success}  Failures: {failures}")
    rate = (success / started * 100.0) if started else 0.0
    print(f"Success rate: {rate:.1f}%")

    print("\nBy Event Type:")
    for k, v in by_type.most_common():
        print(f"  {k}: {v}")

    top_skip = [(k, c) for k, c in skipped_reasons.items() if k]
    if top_skip:
        print("\nTop Skipped Reasons:")
        for k, v in sorted(top_skip, key=lambda x: x[1], reverse=True)[:5]:
            print(f"  {k}: {v}")


@cli.command()
@click.argument("query", required=True)
@click.option(
    "--notify",
    is_flag=True,
    default=False,
    help="Send desktop notifications on completion",
)
def search(query: str, notify: bool):
    """
    Search extracted knowledge.

    Search through concepts, relationships, and insights.
    """
    store = KnowledgeStore()
    extractions = store.load_all()

    if not extractions:
        logger.info("No extractions found. Run 'sync' command first.")
        return

    # Simple text search across all fields
    query_lower = query.lower()
    matches = []

    for extraction in extractions:
        # Search in concepts
        for concept in extraction.get("concepts", []):
            if query_lower in concept.get("name", "").lower() or query_lower in concept.get("description", "").lower():
                matches.append(
                    {
                        "type": "concept",
                        "name": concept.get("name"),
                        "description": concept.get("description"),
                        "source": extraction.get("title", "Unknown"),
                    }
                )

        # Search in relationships
        for rel in extraction.get("relationships", []):
            if (
                query_lower in rel.get("subject", "").lower()
                or query_lower in rel.get("predicate", "").lower()
                or query_lower in rel.get("object", "").lower()
            ):
                matches.append(
                    {
                        "type": "relationship",
                        "triple": f"{rel.get('subject')} --{rel.get('predicate')}--> {rel.get('object')}",
                        "source": extraction.get("title", "Unknown"),
                    }
                )

        # Search in insights
        for insight in extraction.get("insights", []):
            if query_lower in insight.lower():
                matches.append({"type": "insight", "text": insight, "source": extraction.get("title", "Unknown")})

    # Display results
    if not matches:
        logger.info(f"No matches found for '{query}'")
        return

    logger.info(f"\nFound {len(matches)} matches for '{query}':\n")
    for match in matches[:20]:  # Limit to first 20
        if match["type"] == "concept":
            logger.info(f"📌 Concept: {match['name']}")
            logger.info(f"   {match['description'][:100]}...")
            logger.info(f"   Source: {match['source']}\n")
        elif match["type"] == "relationship":
            logger.info(f"🔗 Relationship: {match['triple']}")
            logger.info(f"   Source: {match['source']}\n")
        elif match["type"] == "insight":
            logger.info(f"💡 Insight: {match['text'][:100]}...")
            logger.info(f"   Source: {match['source']}\n")

    if len(matches) > 20:
        logger.info(f"... and {len(matches) - 20} more matches")

    # Send notification for search results
    if notify:
        if matches:
            send_notification(
                title="Amplifier",
                message=f"Found {len(matches)} matches for '{query}'",
                cwd=os.getcwd(),
            )
        else:
            send_notification(
                title="Amplifier",
                message=f"No matches found for '{query}'",
                cwd=os.getcwd(),
            )


@cli.command()
def stats():
    """Show statistics about extracted knowledge."""
    store = KnowledgeStore()
    extractions = store.load_all()

    if not extractions:
        logger.info("No extractions found. Run 'sync' command first.")
        return

    # Calculate statistics
    total_concepts = sum(len(e.get("concepts", [])) for e in extractions)
    total_relationships = sum(len(e.get("relationships", [])) for e in extractions)
    total_insights = sum(len(e.get("insights", [])) for e in extractions)
    total_patterns = sum(len(e.get("patterns", [])) for e in extractions)

    # Display stats
    logger.info("\n" + "=" * 50)
    logger.info("Knowledge Base Statistics")
    logger.info("=" * 50)
    logger.info(f"Items processed: {len(extractions)}")
    logger.info(f"Total concepts: {total_concepts}")
    logger.info(f"Total relationships: {total_relationships}")
    logger.info(f"Total insights: {total_insights}")
    logger.info(f"Total patterns: {total_patterns}")
    logger.info("-" * 50)
    logger.info(f"Avg concepts/item: {total_concepts / len(extractions):.1f}")
    logger.info(f"Avg relationships/item: {total_relationships / len(extractions):.1f}")
    logger.info(f"Avg insights/item: {total_insights / len(extractions):.1f}")


@cli.command()
@click.option("--format", type=click.Choice(["json", "text"]), default="text", help="Output format")
def export(format: str):
    """Export all extracted knowledge."""
    store = KnowledgeStore()
    extractions = store.load_all()

    if not extractions:
        logger.info("No extractions found. Run 'sync' command first.")
        return

    if format == "json":
        # Export as JSON
        output = {"extractions": extractions, "total": len(extractions)}
        print(json.dumps(output, indent=2, ensure_ascii=False))
    else:
        # Export as readable text
        for extraction in extractions:
            print(f"\n{'=' * 60}")
            print(f"Title: {extraction.get('title', 'Unknown')}")
            print(f"Source: {extraction.get('source_id', 'Unknown')}")
            print(f"URL: {extraction.get('url', 'N/A')}")
            print(f"{'=' * 60}")

            if concepts := extraction.get("concepts"):
                print(f"\nConcepts ({len(concepts)}):")
                for concept in concepts[:10]:
                    print(f"  • {concept.get('name')}: {concept.get('description', '')[:80]}...")

            if relationships := extraction.get("relationships"):
                print(f"\nRelationships ({len(relationships)}):")
                for rel in relationships[:10]:
                    print(f"  • {rel.get('subject')} --{rel.get('predicate')}--> {rel.get('object')}")

            if insights := extraction.get("insights"):
                print(f"\nInsights ({len(insights)}):")
                for insight in insights[:5]:
                    print(f"  • {insight[:100]}...")


@cli.command()
@click.option(
    "--notify",
    is_flag=True,
    default=False,
    help="Send desktop notifications on completion",
)
def synthesize(notify: bool):
    """
    Run cross-article synthesis to find patterns and tensions.

    Analyzes all extracted knowledge to find:
    - Entity resolutions (same concept, different names)
    - Contradictions and tensions between articles
    - Emergent insights from pattern analysis
    - Concepts evolving over time
    """
    # Lazy import to avoid circular dependencies
    from .synthesis_engine import SynthesisEngine

    extractions_path = paths.data_dir / "knowledge" / "extractions.jsonl"

    if not extractions_path.exists():
        logger.info("No extractions found. Run 'sync' command first.")
        return

    try:
        # Run synthesis
        engine = SynthesisEngine(extractions_path)
        results = engine.run_synthesis()

        # Print summary
        engine.print_summary(results)

        logger.info(f"\nFull results saved to: {engine.synthesis_path}")

        # Send completion notification
        if notify:
            entity_count = len(results.get("entity_resolutions", []))
            tension_count = len(results.get("contradictions", []))
            insight_count = len(results.get("emergent_insights", []))
            send_notification(
                title="Amplifier",
                message=f"Synthesis complete: {entity_count} entities, {tension_count} tensions, {insight_count} insights",
                cwd=os.getcwd(),
            )
    except KeyboardInterrupt:
        if notify:
            send_notification(
                title="Amplifier",
                message="Synthesis interrupted by user",
                cwd=os.getcwd(),
            )
        raise
    except Exception as e:
        if notify:
            send_notification(
                title="Amplifier",
                message=f"Synthesis failed: {str(e)[:100]}",
                cwd=os.getcwd(),
            )
        raise


@cli.command("gemini-prompt")
@click.option(
    "--domains",
    default="chanoyu",
    help="Comma-separated domain IDs (e.g., 'chanoyu,poa')",
)
@click.option(
    "--output",
    "-o",
    type=click.Path(),
    default=None,
    help="Write prompt to file instead of stdout",
)
def gemini_prompt(domains: str, output: str | None):
    """Generate a Gemini-ready extraction prompt with domain context.

    This outputs a complete prompt that you can paste into Gemini
    along with a book PDF for domain-aware knowledge extraction.

    Examples:
        make knowledge-gemini-prompt DOMAINS=chanoyu
        make knowledge-gemini-prompt DOMAINS=chanoyu,poa
    """
    from .domain_config import build_domain_context

    # Parse and load domain configs
    domain_ids = [d.strip() for d in domains.split(",")]
    domain_contexts = []

    for domain_id in domain_ids:
        config = load_domain_config(domain_id)
        if config:
            context = build_domain_context(config)
            if context:
                domain_contexts.append(context)
                logger.info(f"Loaded domain: {domain_id}")
        else:
            logger.warning(f"Domain config not found: {domain_id}")

    if not domain_contexts:
        logger.error("No valid domain configs found. Use 'domains' command to list available.")
        return

    # Combine domain contexts
    combined_context = "\n\n---\n\n".join(domain_contexts)

    # Build the complete Gemini prompt
    prompt = f"""You are a knowledge extraction specialist. Extract structured knowledge from this book for a personal knowledge vault.

## Domain Context

{combined_context}

## Output Format

Create markdown files with this structure:

### File 1: _book-info.md (always create first)
```yaml
---
title: [Book title in English]
japanese: [日本語タイトル if applicable]
category: source
extracted_date: [Today's date]
extraction_notes: [Any issues or gaps in extraction]
domains: [{", ".join(domain_ids)}]

citation:
  authors:
    - family: [Last name]
      given: [First name/initials]
      japanese: [日本語名 if applicable]
  year: [Publication year]
  title: [Full title including subtitle]
  publisher: [Publisher name]
  publisher_location: [City]
  isbn: [if available]
  pages_total: [total page count]

apa_citation: |
  [Auto-generate based on above fields]
---
```

Include a brief summary of the book's contents, significance, and how it fits into the knowledge domains.

### Content Files: [topic]-[number].md

For each logical section or chapter:

```yaml
---
title: [Section title]
source: [Book title]
category: source
domains: [{", ".join(domain_ids)}]
pages:
  start: [first page number]
  end: [last page number]
page_markers: true
---
```

## Extraction Guidelines

0. **FIRST: Extract complete bibliographic metadata for APA citation**
   - Check title page, copyright page, and colophon for all details

1. **CRITICAL: Preserve page numbers throughout**
   - Include page number for EVERY quote, fact, or significant claim
   - Format: `[p.42]` inline or `(pp. 42-43)` for ranges
   - For quotes: `> "Quote text here" [p.42]`

2. **Preserve original language terms**: Keep original with romaji/translation
   - Format: 茶碗 (chawan, tea bowl)

3. **Focus on domain-relevant content**: Extract concepts, relationships, and insights
   that are relevant to the specified domains above

4. **Extract actionable knowledge**:
   - Key concepts with definitions
   - Relationships between concepts (subject → predicate → object)
   - Philosophical insights and principles
   - Practical techniques or approaches
   - Historical context and lineages

5. **Use tables for lists**: Terminology, concepts, etc. work well as tables:
   | Term | Definition | Domain Relevance |
   |------|------------|------------------|

6. **Note uncertainties**: If meaning is unclear or OCR is ambiguous:
   > [Extraction note: Original text unclear, possibly 〇〇]

7. **Cross-reference across domains**: Note when content bridges multiple domains

8. **Chunk appropriately**:
   - Each file should be 500-1500 words
   - Natural chapter breaks are ideal

## Quality Checks

Before finalizing, verify:
- [ ] All original language characters extracted correctly
- [ ] Frontmatter is valid YAML
- [ ] Every quote has a page number
- [ ] Every factual claim has a page number
- [ ] Content is tagged with relevant domains
- [ ] Major topics from table of contents are covered
"""

    if output:
        from pathlib import Path

        Path(output).write_text(prompt)
        logger.info(f"Prompt written to: {output}")
    else:
        # Print to stdout for easy copying
        print(prompt)


@cli.command()
def domains():
    """List available domain configurations for knowledge extraction.

    Shows both bundled domains (built into amplifier) and user-defined
    domains from ~/switchboard/{domain}/.extraction-config.yaml
    """
    available = list_available_domains()

    if not available:
        logger.info("No domain configurations found.")
        logger.info("")
        logger.info("To create a domain configuration:")
        logger.info("  1. Create ~/switchboard/{domain}/.extraction-config.yaml")
        logger.info("  2. Or use bundled domains in amplifier/knowledge_synthesis/domains/")
        return

    logger.info("Available domain configurations:")
    logger.info("")

    for domain_id in available:
        config = load_domain_config(domain_id)
        if config:
            domain_name = config.get("domain", {}).get("name", domain_id)
            extraction = config.get("extraction", {})
            key_concepts = extraction.get("key_concepts", [])
            concept_count = len(key_concepts)

            logger.info(f"  {domain_id}")
            logger.info(f"    Name: {domain_name}")
            logger.info(f"    Key concepts: {concept_count}")
            if key_concepts:
                preview = ", ".join(str(c).split(" - ")[0] for c in key_concepts[:3])
                logger.info(f"    Preview: {preview}...")
            logger.info("")

    logger.info("Usage: uv run python -m amplifier.knowledge_synthesis.cli sync --domains chanoyu,poa")


@cli.command("gemini-fulltext-prompt")
@click.option(
    "--book",
    default=None,
    help="Book identifier for output template (e.g., 'suzuki-zen-japanese-culture')",
)
@click.option(
    "--output",
    "-o",
    type=click.Path(),
    default=None,
    help="Write prompt to file instead of stdout",
)
def gemini_fulltext_prompt(book: str | None, output: str | None):
    """Generate a Gemini-ready prompt for LOSSLESS full-text extraction.

    Unlike gemini-prompt (which extracts learnings), this creates a complete
    transcription of the book with page markers for later domain-specific extraction.

    The full-text output can then be processed with 'extract-learnings' using
    local Claude, enabling:
    - Re-extraction with different domain focuses
    - Perfect citation capability (full text always available)
    - Cost efficiency (Gemini once, local extraction many times)

    Examples:
        make knowledge-gemini-fulltext-prompt
        make knowledge-gemini-fulltext-prompt BOOK=rikyu-hyakushu
    """
    prompt = """You are a precise text transcription specialist. Your task is to create a
complete, lossless markdown transcription of this PDF book.

## CRITICAL REQUIREMENTS

### 1. Page Markers (MOST IMPORTANT)
- Insert `<!-- PAGE: n -->` marker at the START of each page's content
- Every page boundary must be marked
- Page numbers enable precise citations later
- If page numbers restart (e.g., roman numerals for preface), note: `<!-- PAGE: xii (preface) -->`

### 2. Complete Transcription
- Transcribe ALL text, not just "key points"
- This is a LOSSLESS extraction - nothing should be summarized or omitted
- Preserve paragraph structure
- Maintain heading hierarchy (use #, ##, ###)
- Keep original punctuation and formatting

### 3. Japanese/Original Language Text
- Preserve ALL kanji, hiragana, katakana EXACTLY as written
- Add romaji in parentheses for specialized terms on first occurrence
- Format: 茶道 (chadō)
- Keep original-language quotations intact

### 4. Tables and Lists
- Recreate tables in markdown format
- Preserve numbered and bulleted lists
- Maintain original ordering

### 5. Quotations
- Use blockquote (>) for quotations
- Preserve quotation attribution
- Note if translation vs original: > "Quote" [Author, p.X, translated]

### 6. Figures and Images
- Insert placeholder: `[Figure X.Y: brief description]`
- Preserve captions exactly
- Note if figure has Japanese labels

### 7. Footnotes/Endnotes
- Preserve using markdown footnote syntax: [^1]
- Place footnote content at end of chapter or document
- Keep original numbering

## OUTPUT FORMAT

Create TWO files:

### File 1: _book-info.md

```yaml
---
title: "[Full title in original language]"
title_translated: "[English translation if different]"
japanese: "[日本語タイトル if applicable]"
category: source
type: full-text-extraction
extraction_date: "[Today's date: YYYY-MM-DD]"
extraction_method: gemini-lossless-v1
total_pages: [n]
page_range: "[first readable page]-[last readable page]"
language_primary: "[e.g., English, Japanese]"
language_secondary: "[if bilingual]"
has_japanese_text: [true/false]
has_figures: [true/false]
has_tables: [true/false]

citation:
  authors:
    - family: "[Family name]"
      given: "[Given name/initials]"
      japanese: "[日本語名 if applicable]"
  year: [YYYY]
  title: "[Full title including subtitle]"
  title_original: "[Original language title if translated work]"
  publisher: "[Publisher name]"
  publisher_location: "[City]"
  edition: "[e.g., 2nd ed., if applicable]"
  isbn: "[if available]"
  pages_total: [n]
  translator: "[if applicable]"

apa_citation: |
  [Generate proper APA 7th edition citation]
---

## About This Book

[Write a 2-3 paragraph summary of:
1. What this book is about
2. Who the author is and their significance
3. Why this book matters for the knowledge domains it covers]

## Structure

[List chapters/sections with page numbers in a table format]

| Chapter | Title | Pages |
|---------|-------|-------|
| Preface | [title] | pp. i-x |
| 1 | [title] | pp. 1-25 |
| ... | ... | ... |

## Extraction Notes

[Note any issues encountered:
- Unclear text or OCR problems
- Missing pages
- Image-heavy sections that couldn't be fully captured
- Unusual formatting]
```

### File 2: _full-text.md

```markdown
---
title: "[Book Title] - Full Text"
source_type: lossless-extraction
page_count: [n]
---

<!-- PAGE: i (front matter) -->
# [Title Page Content]

[Author name, publisher, year, etc.]

<!-- PAGE: ii -->
[Copyright page content]

<!-- PAGE: iii -->
# Contents

[Full table of contents]

<!-- PAGE: 1 -->
# Preface

[Complete preface text, preserving all paragraphs...]

Lorem ipsum paragraph one...

Lorem ipsum paragraph two...

<!-- PAGE: 5 -->
[Preface continues...]

<!-- PAGE: 10 -->
# Chapter I: [Full Chapter Title]

## [Section heading if any]

[Complete chapter text, every paragraph, every sentence...]

> "Any quotations preserved exactly" [p. 10]

[Continue transcribing EVERYTHING...]

<!-- PAGE: 11 -->
[Chapter continues with new page marker at each boundary...]

[... continue for entire book ...]

<!-- PAGE: 320 -->
# Bibliography

[Complete bibliography if present]

<!-- PAGE: 325 -->
# Index

[Include index if present - can be in list format]
```

## QUALITY CHECKLIST

Before completing, verify:
- [ ] EVERY page has a `<!-- PAGE: n -->` marker at its start
- [ ] NO content was summarized - this is FULL transcription
- [ ] All Japanese/original characters preserved correctly (not romanized)
- [ ] Paragraph structure maintained (blank lines between paragraphs)
- [ ] All headings use proper markdown hierarchy
- [ ] Tables formatted correctly
- [ ] Quotations use > blockquote format
- [ ] Frontmatter is valid YAML
- [ ] Page numbers are sequential and complete
- [ ] Footnotes preserved with [^n] syntax
- [ ] Figure placeholders inserted for images

## IMPORTANT

This is a TRANSCRIPTION, not an extraction or summary. The goal is to have the
complete text available for later processing. Domain-specific knowledge extraction
will happen in a separate step using this full text.

If the book is very long (500+ pages), you may split _full-text.md into multiple
files by major section:
- _full-text-part1.md (Preface + Chapters 1-5)
- _full-text-part2.md (Chapters 6-10)
- etc.

Each part should start with a YAML header noting the page range.
"""

    if book:
        prompt = f"# Full-Text Extraction: {book}\n\n" + prompt
        logger.info(f"Generated prompt for book: {book}")

    if output:
        from pathlib import Path

        Path(output).write_text(prompt)
        logger.info(f"Prompt written to: {output}")
    else:
        print(prompt)


@cli.command("extract-learnings")
@click.option(
    "--source",
    required=True,
    type=click.Path(exists=True),
    help="Path to source directory containing _full-text.md",
)
@click.option(
    "--domains",
    default="chanoyu",
    help="Comma-separated domain IDs for focused extraction",
)
@click.option(
    "--pages-per-chunk",
    default=15,
    type=int,
    help="Number of pages per processing chunk (default: 15)",
)
@click.option(
    "--notify",
    is_flag=True,
    default=False,
    help="Send desktop notifications on completion",
)
def extract_learnings(source: str, domains: str, pages_per_chunk: int, notify: bool):
    """Extract domain-specific learnings from a full-text source.

    This is Phase 2 of the lossless ingest workflow. It reads _full-text.md
    and extracts domain-specific concepts, relationships, and insights using
    local Claude (not Gemini), enabling:

    - Re-extraction with different domain focuses (cheap!)
    - Perfect citations (full text available)
    - Incremental domain additions

    Examples:
        make knowledge-extract-learnings SOURCE=~/switchboard/chanoyu/sources/suzuki DOMAINS=chanoyu
        make knowledge-extract-learnings SOURCE=~/switchboard/chanoyu/sources/suzuki DOMAINS=poa
    """
    from pathlib import Path

    source_path = Path(source).expanduser()

    # Find full-text file
    full_text_file = source_path / "_full-text.md"
    if not full_text_file.exists():
        # Try finding parts
        parts = list(source_path.glob("_full-text-part*.md"))
        if not parts:
            logger.error(f"No _full-text.md found in {source_path}")
            logger.error("Run gemini-fulltext-prompt first and save output to _full-text.md")
            return
        logger.info(f"Found {len(parts)} full-text parts")
    else:
        logger.info(f"Found: {full_text_file}")

    # Load book info
    book_info_file = source_path / "_book-info.md"
    book_title = source_path.name
    if book_info_file.exists():
        import yaml

        content = book_info_file.read_text()
        if "---" in content:
            yaml_part = content.split("---")[1]
            try:
                meta = yaml.safe_load(yaml_part)
                book_title = meta.get("title", book_title)
            except Exception:
                pass
        logger.info(f"Book: {book_title}")

    # Parse domains
    domain_ids = [d.strip() for d in domains.split(",")]
    logger.info(f"Domains: {', '.join(domain_ids)}")

    # Load domain configs
    from .domain_config import build_domain_context
    from .domain_config import load_domain_config

    domain_contexts = []
    for domain_id in domain_ids:
        config = load_domain_config(domain_id)
        if config:
            context = build_domain_context(config)
            if context:
                domain_contexts.append((domain_id, context, config))
                logger.info(f"  ✓ Loaded: {domain_id}")
        else:
            logger.warning(f"  ✗ Not found: {domain_id}")

    if not domain_contexts:
        logger.error("No valid domain configs found")
        return

    # Read full text
    if full_text_file.exists():
        full_text = full_text_file.read_text()
    else:
        parts = sorted(source_path.glob("_full-text-part*.md"))
        full_text = "\n\n".join(p.read_text() for p in parts)

    # Chunk by pages
    import re

    page_pattern = re.compile(r"<!-- PAGE: (\d+|[ivxlc]+)(?:\s*\([^)]+\))? -->", re.IGNORECASE)
    pages = page_pattern.split(full_text)

    if len(pages) < 3:
        logger.warning("No page markers found. Processing as single chunk.")
        chunks = [(full_text, "1", "end")]
    else:
        # Reconstruct chunks with page info
        chunks = []
        for i in range(0, len(pages) - 1, pages_per_chunk * 2):
            chunk_content = ""
            start_page = None
            end_page = None
            for j in range(i, min(i + pages_per_chunk * 2, len(pages) - 1), 2):
                page_num = pages[j + 1] if j + 1 < len(pages) else "?"
                page_text = pages[j + 2] if j + 2 < len(pages) else ""
                if start_page is None:
                    start_page = page_num
                end_page = page_num
                chunk_content += f"<!-- PAGE: {page_num} -->\n{page_text}\n\n"
            if chunk_content.strip():
                chunks.append((chunk_content, start_page or "?", end_page or "?"))

    logger.info(f"Split into {len(chunks)} chunks ({pages_per_chunk} pages each)")

    # Create output directory
    learnings_dir = source_path / "learnings"
    learnings_dir.mkdir(exist_ok=True)

    # Process each domain
    asyncio.run(
        _extract_learnings_async(
            chunks=chunks,
            domain_contexts=domain_contexts,
            book_title=book_title,
            learnings_dir=learnings_dir,
            notify=notify,
        )
    )


async def _extract_learnings_async(
    chunks: list[tuple[str, str, str]],
    domain_contexts: list[tuple[str, str, dict]],
    book_title: str,
    learnings_dir,
    notify: bool,
):
    """Async extraction of learnings from chunks."""
    from amplifier.knowledge_integration import UnifiedKnowledgeExtractor

    extractor = UnifiedKnowledgeExtractor()

    for domain_id, domain_context, _domain_config in domain_contexts:
        logger.info(f"\n{'=' * 50}")
        logger.info(f"Extracting for domain: {domain_id}")
        logger.info(f"{'=' * 50}")

        all_concepts = []
        all_relationships = []
        all_insights = []

        for idx, (chunk_text, start_page, end_page) in enumerate(chunks):
            logger.info(f"  Processing chunk {idx + 1}/{len(chunks)} (pp. {start_page}-{end_page})...")

            try:
                # Build extraction prompt with domain context
                prompt_prefix = f"""You are extracting domain-specific knowledge from a book.

## Domain Context
{domain_context}

## Source
Book: {book_title}
Pages: {start_page} - {end_page}

## Instructions
Extract concepts, relationships, and insights relevant to the domain above.
Every extracted item MUST include the page reference [p.X] from the source text.
Focus on what's most valuable for understanding and practicing in this domain.

## Source Text
"""
                # Extract using existing extractor
                result = await extractor.extract_from_text(
                    text=prompt_prefix + chunk_text,
                    title=f"{book_title} (pp. {start_page}-{end_page})",
                    source=domain_id,
                )

                if result.concepts:
                    all_concepts.extend(result.concepts)
                if result.relationships:
                    all_relationships.extend(result.relationships)
                if result.key_insights:
                    all_insights.extend(result.key_insights)

                logger.info(f"    → {len(result.concepts)} concepts, {len(result.relationships)} relationships")

            except Exception as e:
                logger.error(f"    ✗ Error: {e}")
                continue

        # Save domain-specific outputs
        domain_file = learnings_dir / f"{domain_id}-insights.md"

        # Generate markdown summary
        output_lines = [
            "---",
            f"title: {book_title} - {domain_id.title()} Insights",
            f"domain: {domain_id}",
            f"extracted_date: {__import__('datetime').date.today().isoformat()}",
            f"concept_count: {len(all_concepts)}",
            f"relationship_count: {len(all_relationships)}",
            f"insight_count: {len(all_insights)}",
            "---",
            "",
            f"# {book_title}",
            f"## Domain: {domain_id.title()}",
            "",
            "---",
            "",
        ]

        if all_concepts:
            output_lines.append("## Key Concepts")
            output_lines.append("")
            for concept in all_concepts:
                name = concept.get("name", "Unknown")
                desc = concept.get("description", "")
                output_lines.append(f"### {name}")
                output_lines.append(f"{desc}")
                output_lines.append("")

        if all_insights:
            output_lines.append("## Insights")
            output_lines.append("")
            for insight in all_insights:
                output_lines.append(f"- {insight}")
            output_lines.append("")

        if all_relationships:
            output_lines.append("## Relationships")
            output_lines.append("")
            output_lines.append("| Subject | Predicate | Object |")
            output_lines.append("|---------|-----------|--------|")
            for rel in all_relationships[:50]:  # Limit for readability
                output_lines.append(f"| {rel.subject} | {rel.predicate} | {rel.object} |")
            output_lines.append("")

        domain_file.write_text("\n".join(output_lines))
        logger.info(f"\n✓ Saved: {domain_file}")

        # Also save as JSONL for knowledge graph
        jsonl_file = learnings_dir / f"{domain_id}-extractions.jsonl"
        import json

        with open(jsonl_file, "w") as f:
            extraction = {
                "source": book_title,
                "domain": domain_id,
                "concepts": all_concepts,
                "relationships": [
                    {"subject": r.subject, "predicate": r.predicate, "object": r.object, "confidence": r.confidence}
                    for r in all_relationships
                ],
                "insights": all_insights,
            }
            f.write(json.dumps(extraction, ensure_ascii=False) + "\n")
        logger.info(f"✓ Saved: {jsonl_file}")

    logger.info(f"\n{'=' * 50}")
    logger.info("EXTRACTION COMPLETE")
    logger.info(f"Output directory: {learnings_dir}")
    logger.info(f"{'=' * 50}")

    if notify:
        send_notification(
            title="Amplifier",
            message=f"Learnings extraction complete for {book_title}",
            cwd=os.getcwd(),
        )


if __name__ == "__main__":
    cli()
