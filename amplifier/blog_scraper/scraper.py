"""Blog scraper for joi.ito.com.

Crawls the blog and extracts posts to markdown with YAML frontmatter.
Supports incremental scraping with --since parameter.
Uses curl for reliable SSL handling with Cloudflare-protected sites.
"""

import logging
import re
import subprocess
import time
from datetime import datetime
from pathlib import Path
from urllib.parse import urljoin
from urllib.parse import urlparse

from bs4 import BeautifulSoup
from markdownify import markdownify as md

from amplifier.blog_scraper.models import BlogPost
from amplifier.blog_scraper.models import ScrapeResult

logger = logging.getLogger(__name__)

# Rate limiting
REQUEST_DELAY = 0.5  # seconds between requests

# URL patterns - no $ anchor to allow query params after .html
EN_POST_PATTERN = re.compile(r"/weblog/(\d{4})/(\d{2})/(\d{2})/([^/?&#]+)\.html")
JP_POST_PATTERN = re.compile(r"/jp/archives/(\d{4})/(\d{2})/(\d{2})/(\d+)\.html")

# Social share URLs to exclude
SOCIAL_SHARE_DOMAINS = {"twitter.com", "facebook.com", "linkedin.com", "reddit.com"}


def _fetch_url(url: str, timeout: int = 30) -> tuple[str, int]:
    """Fetch URL content using curl (handles Cloudflare SSL properly).

    Returns:
        Tuple of (html_content, status_code)
    """
    try:
        result = subprocess.run(
            [
                "curl",
                "-s",
                "-L",  # Follow redirects
                "-w", "%{http_code}",  # Write status code at end
                "-o", "-",  # Write body to stdout
                "--max-time", str(timeout),
                "-A", "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
                url,
            ],
            capture_output=True,
            text=True,
            timeout=timeout + 5,
        )
        # Status code is the last 3 characters
        if len(result.stdout) >= 3:
            status_code = int(result.stdout[-3:])
            html = result.stdout[:-3]
        else:
            status_code = 0
            html = result.stdout
        return html, status_code
    except Exception as e:
        logger.error(f"  curl failed for {url}: {e}")
        return "", 0


def scrape_blog(
    output_dir: Path,
    languages: list[str] | None = None,
    since: datetime | None = None,
    max_posts: int | None = None,
    base_url: str = "https://joi.ito.com",
) -> ScrapeResult:
    """Scrape blog posts to markdown files.

    Args:
        output_dir: Directory to save markdown files
        languages: Languages to scrape ["en", "jp"] (default: both)
        since: Only scrape posts after this date
        max_posts: Maximum posts to scrape (for testing)
        base_url: Base URL of the blog

    Returns:
        ScrapeResult with statistics
    """
    if languages is None:
        languages = ["en", "jp"]

    result = ScrapeResult(output_dir=output_dir)

    for lang in languages:
        logger.info(f"Scraping {lang.upper()} posts...")
        if lang == "en":
            post_urls = _discover_english_posts(base_url, since, max_posts)
        else:
            post_urls = _discover_japanese_posts(base_url, since, max_posts)

        for url in post_urls:
            try:
                post = scrape_post(url, lang)
                if post:
                    output_path = post.output_path(output_dir)
                    output_path.parent.mkdir(parents=True, exist_ok=True)
                    output_path.write_text(post.to_markdown(), encoding="utf-8")
                    result.posts_scraped += 1
                    logger.info(f"  Saved: {output_path.relative_to(output_dir)}")
                else:
                    result.posts_skipped += 1
            except Exception as e:
                result.add_error(url, str(e))
                logger.warning(f"  Failed: {url} - {e}")

            time.sleep(REQUEST_DELAY)

    return result


def scrape_post(url: str, language: str = "en") -> BlogPost | None:
    """Scrape a single blog post.

    Args:
        url: Post URL
        language: Language code ("en" or "jp")

    Returns:
        BlogPost or None if parsing fails
    """
    html, status = _fetch_url(url)
    if status != 200:
        logger.warning(f"  Got status {status} for {url}")
        return None

    soup = BeautifulSoup(html, "html.parser")

    # Extract title - try multiple strategies
    title_elem = (
        soup.find("h1", class_="entry-title")
        or soup.find("h2", class_="entry-title")
        or soup.find("h1", class_="post-title")
        or soup.find(class_="entry-title")
        or soup.find("h1")
        or soup.find("title")
    )
    if not title_elem:
        return None
    title = title_elem.get_text(strip=True)
    # Clean up title (remove site name suffix and trailing symbols)
    title = re.sub(r"\s*[|\-]\s*Joi Ito.*$", "", title)
    title = re.sub(r"[»«]+$", "", title).strip()

    # Extract date from URL
    parsed_url = urlparse(url)
    if language == "en":
        match = EN_POST_PATTERN.search(parsed_url.path)
    else:
        match = JP_POST_PATTERN.search(parsed_url.path)

    if not match:
        logger.warning(f"Could not parse date from URL: {url}")
        return None

    year, month, day = int(match.group(1)), int(match.group(2)), int(match.group(3))
    post_date = datetime(year, month, day)  # noqa: DTZ001 - dates from URLs have no timezone

    # Extract content - look for common blog content containers
    content_elem = (
        soup.find("div", class_="entry-content")
        or soup.find("div", class_="entry-body")
        or soup.find("article")
        or soup.find("div", class_="post-body")
        or soup.find("div", id="content")
    )

    if not content_elem:
        # Fallback: find main content area
        main = soup.find("main") or soup.find("div", role="main")
        if main:
            content_elem = main

    if not content_elem:
        logger.warning(f"Could not find content container: {url}")
        return None

    content_html = str(content_elem)

    # Convert to markdown
    content_markdown = _html_to_markdown(content_html)

    # Extract categories
    categories = []
    category_links = soup.find_all("a", rel="category tag") or soup.find_all(
        "a", class_="category"
    )
    for cat in category_links:
        cat_text = cat.get_text(strip=True)
        if cat_text:
            categories.append(cat_text)

    return BlogPost(
        title=title,
        permalink=url,
        content_html=content_html,
        content_markdown=content_markdown,
        date=post_date,
        language=language,
        categories=categories,
        source_path=parsed_url.path,
    )


def _html_to_markdown(html: str) -> str:
    """Convert HTML to clean markdown."""
    # Configure markdownify
    markdown = md(
        html,
        heading_style="ATX",  # Use # headers
        bullets="-",  # Use - for lists
        strip=["script", "style", "nav", "footer", "aside"],
    )

    # Clean up excessive whitespace
    markdown = re.sub(r"\n{3,}", "\n\n", markdown)
    markdown = markdown.strip()

    return markdown


def _get_monthly_archive_urls(html: str, archive_id: str) -> list[str]:
    """Extract monthly archive URLs from the dropdown select element.

    Args:
        html: HTML content of the page
        archive_id: The ID of the select element (e.g., 'mth-archives-dropdown')

    Returns:
        List of monthly archive URLs sorted by date (newest first)
    """
    soup = BeautifulSoup(html, "html.parser")
    dropdown = soup.find("select", id=archive_id)
    if not dropdown:
        return []

    urls = []
    for option in dropdown.find_all("option"):
        value = option.get("value", "")
        if value and value.startswith("http"):
            urls.append(value)

    return urls


def _discover_english_posts(
    base_url: str,
    since: datetime | None,
    max_posts: int | None,
) -> list[str]:
    """Discover English post URLs by crawling monthly archive pages."""
    posts: list[str] = []
    seen_urls: set[str] = set()

    # Step 1: Fetch main page to get monthly archive URLs
    logger.info("  Fetching EN monthly archives list...")
    html, status = _fetch_url(f"{base_url}/weblog/")
    if status != 200:
        logger.error(f"  Failed to fetch EN main page: status {status}")
        return posts

    # Extract monthly archive URLs from dropdown
    monthly_urls = _get_monthly_archive_urls(html, "mth-archives-dropdown")
    logger.info(f"  Found {len(monthly_urls)} monthly archives")

    if not monthly_urls:
        # Fallback: try alternate dropdown ID
        monthly_urls = _get_monthly_archive_urls(html, "monthly-archives")

    # Step 2: Also extract posts from main page
    soup = BeautifulSoup(html, "html.parser")
    for link in soup.find_all("a", href=True):
        href = str(link["href"])
        if any(domain in href for domain in SOCIAL_SHARE_DOMAINS):
            continue
        if EN_POST_PATTERN.search(href):
            full_url = urljoin(base_url, href)
            normalized_url = full_url.split("#")[0].split("?")[0]
            if normalized_url not in seen_urls:
                seen_urls.add(normalized_url)
                if since:
                    match = EN_POST_PATTERN.search(href)
                    if match:
                        post_date = datetime(int(match.group(1)), int(match.group(2)), int(match.group(3)))  # noqa: DTZ001
                        if post_date < since:
                            continue
                posts.append(normalized_url)
                if max_posts and len(posts) >= max_posts:
                    return posts

    # Step 3: Crawl each monthly archive
    for archive_url in monthly_urls:
        if max_posts and len(posts) >= max_posts:
            break

        # Extract year/month from URL for logging and date filtering
        # URL format: https://joi.ito.com/weblog/YYYY/MM/
        match = re.search(r"/weblog/(\d{4})/(\d{2})/?", archive_url)
        if match:
            year, month = int(match.group(1)), int(match.group(2))
            if since and datetime(year, month, 1) < since.replace(day=1):  # noqa: DTZ001
                logger.info(f"  Skipping {year}/{month:02d} (before --since date)")
                continue
            logger.info(f"  Crawling EN archive {year}/{month:02d}...")
        else:
            logger.info(f"  Crawling EN archive: {archive_url}")

        time.sleep(REQUEST_DELAY)
        html, status = _fetch_url(archive_url)
        if status != 200:
            logger.warning(f"  Failed to fetch {archive_url}: status {status}")
            continue

        soup = BeautifulSoup(html, "html.parser")
        for link in soup.find_all("a", href=True):
            href = str(link["href"])
            if any(domain in href for domain in SOCIAL_SHARE_DOMAINS):
                continue
            if EN_POST_PATTERN.search(href):
                full_url = urljoin(base_url, href)
                normalized_url = full_url.split("#")[0].split("?")[0]
                if normalized_url not in seen_urls:
                    seen_urls.add(normalized_url)
                    if since:
                        match = EN_POST_PATTERN.search(href)
                        if match:
                            post_date = datetime(int(match.group(1)), int(match.group(2)), int(match.group(3)))  # noqa: DTZ001
                            if post_date < since:
                                continue
                    posts.append(normalized_url)
                    if max_posts and len(posts) >= max_posts:
                        return posts

    logger.info(f"  Discovered {len(posts)} EN posts total")
    return posts


def _discover_japanese_posts(
    base_url: str,
    since: datetime | None,
    max_posts: int | None,
) -> list[str]:
    """Discover Japanese post URLs by crawling monthly archive pages."""
    posts: list[str] = []
    seen_urls: set[str] = set()

    # Step 1: Fetch main page to get monthly archive URLs
    logger.info("  Fetching JP monthly archives list...")
    html, status = _fetch_url(f"{base_url}/jp/")
    if status != 200:
        logger.error(f"  Failed to fetch JP main page: status {status}")
        return posts

    # Extract monthly archive URLs from dropdown
    monthly_urls = _get_monthly_archive_urls(html, "mth-archives-dropdown")
    logger.info(f"  Found {len(monthly_urls)} monthly archives")

    if not monthly_urls:
        # Fallback: try alternate dropdown ID
        monthly_urls = _get_monthly_archive_urls(html, "monthly-archives")

    # Step 2: Also extract posts from main page
    soup = BeautifulSoup(html, "html.parser")
    for link in soup.find_all("a", href=True):
        href = str(link["href"])
        if any(domain in href for domain in SOCIAL_SHARE_DOMAINS):
            continue
        if JP_POST_PATTERN.search(href):
            full_url = urljoin(base_url, href)
            normalized_url = full_url.split("#")[0].split("?")[0]
            if normalized_url not in seen_urls:
                seen_urls.add(normalized_url)
                if since:
                    match = JP_POST_PATTERN.search(href)
                    if match:
                        post_date = datetime(int(match.group(1)), int(match.group(2)), int(match.group(3)))  # noqa: DTZ001
                        if post_date < since:
                            continue
                posts.append(normalized_url)
                if max_posts and len(posts) >= max_posts:
                    return posts

    # Step 3: Crawl each monthly archive
    for archive_url in monthly_urls:
        if max_posts and len(posts) >= max_posts:
            break

        # Extract year/month from URL for logging and date filtering
        # URL format: https://joi.ito.com/jp/archives/YYYY/MM/
        match = re.search(r"/jp/archives/(\d{4})/(\d{2})/?", archive_url)
        if match:
            year, month = int(match.group(1)), int(match.group(2))
            if since and datetime(year, month, 1) < since.replace(day=1):  # noqa: DTZ001
                logger.info(f"  Skipping {year}/{month:02d} (before --since date)")
                continue
            logger.info(f"  Crawling JP archive {year}/{month:02d}...")
        else:
            logger.info(f"  Crawling JP archive: {archive_url}")

        time.sleep(REQUEST_DELAY)
        html, status = _fetch_url(archive_url)
        if status != 200:
            logger.warning(f"  Failed to fetch {archive_url}: status {status}")
            continue

        soup = BeautifulSoup(html, "html.parser")
        for link in soup.find_all("a", href=True):
            href = str(link["href"])
            if any(domain in href for domain in SOCIAL_SHARE_DOMAINS):
                continue
            if JP_POST_PATTERN.search(href):
                full_url = urljoin(base_url, href)
                normalized_url = full_url.split("#")[0].split("?")[0]
                if normalized_url not in seen_urls:
                    seen_urls.add(normalized_url)
                    if since:
                        match = JP_POST_PATTERN.search(href)
                        if match:
                            post_date = datetime(int(match.group(1)), int(match.group(2)), int(match.group(3)))  # noqa: DTZ001
                            if post_date < since:
                                continue
                    posts.append(normalized_url)
                    if max_posts and len(posts) >= max_posts:
                        return posts

    logger.info(f"  Discovered {len(posts)} JP posts total")
    return posts
