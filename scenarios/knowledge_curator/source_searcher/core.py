#!/usr/bin/env python3
"""
Source Searcher - Searches for authoritative sources for claims.

Uses academic search APIs (Semantic Scholar, CrossRef, arXiv, CiNii) to find citations.
Supports domain-specific configuration via CitationRules for customized search behavior.
"""

import asyncio
import re
import xml.etree.ElementTree as ET
from typing import Any

import httpx
from pydantic import BaseModel

from amplifier.utils.logger import get_logger
from scenarios.knowledge_curator.citation_rules import DEFAULT_RULES
from scenarios.knowledge_curator.citation_rules import CitationRules

logger = get_logger(__name__)

# API endpoints
SEMANTIC_SCHOLAR_API = "https://api.semanticscholar.org/graph/v1/paper/search"
CROSSREF_API = "https://api.crossref.org/works"
ARXIV_API = "https://export.arxiv.org/api/query"
CINII_API = "https://cir.nii.ac.jp/opensearch/all"  # CiNii Research OpenSearch


class Source(BaseModel):
    """An authoritative source for a claim."""

    title: str
    authors: list[str]
    year: int | None = None
    doi: str | None = None
    url: str | None = None
    source_type: str  # paper, book, article, website
    relevance_score: float  # 0-1 how relevant to the claim
    claim_index: int  # Which claim this source supports


class SourceSearcher:
    """Searches for authoritative sources to support claims.

    Uses CitationRules for domain-specific search behavior including:
    - Domain qualifier injection for focused queries
    - Term mappings for bilingual search (e.g., English→Japanese)
    - Irrelevant keyword filtering with configurable penalties
    - Configurable relevance thresholds
    - Customizable search source selection
    """

    def __init__(
        self,
        rules: CitationRules | None = None,
        timeout: float = 30.0,
        max_results_per_claim: int = 3,
    ):
        self.rules = rules or DEFAULT_RULES
        self.timeout = timeout
        self.max_results_per_claim = max_results_per_claim
        self._client: httpx.AsyncClient | None = None

        if self.rules.domain_name:
            logger.info(f"SourceSearcher initialized for domain: {self.rules.domain_name}")

    async def __aenter__(self):
        self._client = httpx.AsyncClient(timeout=self.timeout)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._client:
            await self._client.aclose()

    @property
    def client(self) -> httpx.AsyncClient:
        if self._client is None:
            raise RuntimeError("SourceSearcher must be used as async context manager")
        return self._client

    async def search_sources(self, claims: list[dict[str, Any]]) -> list[Source]:
        """Search for sources that support the given claims.

        Uses CitationRules to determine:
        - Whether to apply domain-specific search strategies
        - Which search sources to query
        - How to translate terms for bilingual search
        """
        sources = []

        for i, claim in enumerate(claims):
            claim_text = claim.get("text", "")
            # category can be used later for specialized search strategies
            _ = claim.get("category", "factual")

            try:
                # Extract search terms from claim
                search_terms = self._extract_search_terms(claim_text)
                if not search_terms:
                    logger.debug(f"No search terms extracted from claim {i}")
                    continue

                # Check if this is domain-specific content (based on term_mappings)
                has_domain_content = self.rules.has_domain_content(claim_text)

                # Build list of search tasks
                search_tasks = []

                if has_domain_content and self.rules.term_mappings:
                    # Translate to target language (e.g., Japanese) for better results
                    translated_terms = self.rules.translate_to_target_language(claim_text)

                    # Add domain context to queries to avoid irrelevant results
                    if self.rules.domain_qualifier:
                        search_terms = f"{search_terms} {self.rules.domain_qualifier}"

                    if translated_terms:
                        logger.info(
                            f"Claim {i}: Searching translated: '{translated_terms[:30]}...' "
                            f"and original: '{search_terms[:30]}...'"
                        )

                        # Search based on configured sources
                        for source_name in self.rules.search_sources:
                            if source_name == "cinii":
                                # CiNii gets both translated and original queries
                                search_tasks.append(self._search_cinii(translated_terms))
                                search_tasks.append(self._search_cinii(search_terms))
                            elif source_name == "semantic_scholar":
                                search_tasks.append(self._search_semantic_scholar(search_terms))
                            elif source_name == "crossref":
                                search_tasks.append(self._search_crossref(search_terms))
                            elif source_name == "arxiv":
                                search_tasks.append(self._search_arxiv(search_terms))
                    else:
                        logger.info(
                            f"Claim {i}: Domain content but no translation, searching: '{search_terms[:50]}...'"
                        )
                        for source_name in self.rules.search_sources:
                            if source_name == "cinii":
                                search_tasks.append(self._search_cinii(search_terms))
                            elif source_name == "semantic_scholar":
                                search_tasks.append(self._search_semantic_scholar(search_terms))
                            elif source_name == "crossref":
                                search_tasks.append(self._search_crossref(search_terms))
                            elif source_name == "arxiv":
                                search_tasks.append(self._search_arxiv(search_terms))
                else:
                    logger.info(f"Searching for claim {i}: '{search_terms[:50]}...'")
                    # Standard search using configured sources (default: semantic_scholar, crossref, arxiv)
                    for source_name in self.rules.search_sources:
                        if source_name == "cinii":
                            search_tasks.append(self._search_cinii(search_terms))
                        elif source_name == "semantic_scholar":
                            search_tasks.append(self._search_semantic_scholar(search_terms))
                        elif source_name == "crossref":
                            search_tasks.append(self._search_crossref(search_terms))
                        elif source_name == "arxiv":
                            search_tasks.append(self._search_arxiv(search_terms))

                # Search multiple sources in parallel
                results = await asyncio.gather(*search_tasks, return_exceptions=True)

                # Combine results from all sources
                found_sources: list[Source] = []
                for result in results:
                    if isinstance(result, BaseException):
                        logger.debug(f"Search error: {result}")
                        continue
                    if isinstance(result, list):
                        found_sources.extend(result)

                # Score and deduplicate
                scored_sources = self._score_and_dedupe(found_sources, claim_text)

                # Take top N results
                for source in scored_sources[: self.max_results_per_claim]:
                    source.claim_index = i
                    sources.append(source)

                logger.info(f"Found {len(scored_sources)} sources for claim {i}")

            except Exception as e:
                logger.warning(f"Error searching for claim {i}: {e}")

        return sources

    def _extract_search_terms(self, claim_text: str) -> str:
        """Extract key search terms from a claim."""
        # Remove markdown formatting
        text = re.sub(r"\[.*?\]\(.*?\)", "", claim_text)
        text = re.sub(r"[*_`#]", "", text)

        # Remove very short words and common words
        stop_words = {
            "the",
            "a",
            "an",
            "is",
            "are",
            "was",
            "were",
            "be",
            "been",
            "being",
            "have",
            "has",
            "had",
            "do",
            "does",
            "did",
            "will",
            "would",
            "could",
            "should",
            "may",
            "might",
            "can",
            "this",
            "that",
            "these",
            "those",
            "and",
            "or",
            "but",
            "if",
            "then",
            "so",
            "as",
            "of",
            "in",
            "on",
            "at",
            "to",
            "for",
            "with",
            "from",
            "by",
            "about",
            "into",
            "through",
            "during",
            "before",
            "after",
            "above",
            "below",
            "between",
            "under",
            "again",
            "further",
            "once",
            "more",
            "most",
            "other",
            "some",
            "such",
            "only",
            "own",
            "same",
            "than",
            "too",
            "very",
            "just",
            "also",
            "now",
            "here",
            "there",
            "when",
            "where",
            "why",
            "how",
            "all",
            "each",
            "few",
            "no",
            "nor",
            "not",
        }

        words = [w.lower() for w in text.split() if len(w) > 2]
        meaningful = [w for w in words if w not in stop_words]

        # Take first 8 meaningful words as search query (slightly longer for better results)
        return " ".join(meaningful[:8])

    async def _search_semantic_scholar(self, query: str) -> list[Source]:
        """Search Semantic Scholar for papers."""
        sources = []
        try:
            params = {
                "query": query,
                "limit": 5,
                "fields": "title,authors,year,externalIds,url",
            }

            response = await self.client.get(SEMANTIC_SCHOLAR_API, params=params)

            if response.status_code == 429:
                logger.warning("Semantic Scholar rate limited")
                return []

            if response.status_code != 200:
                logger.debug(f"Semantic Scholar returned {response.status_code}")
                return []

            data = response.json()
            papers = data.get("data", [])

            for paper in papers:
                # Extract authors
                authors = []
                for author in paper.get("authors", []):
                    if author.get("name"):
                        authors.append(author["name"])

                # Extract DOI
                external_ids = paper.get("externalIds", {}) or {}
                doi = external_ids.get("DOI")

                source = Source(
                    title=paper.get("title", "Unknown"),
                    authors=authors[:5],  # Limit to 5 authors
                    year=paper.get("year"),
                    doi=doi,
                    url=paper.get("url"),
                    source_type="paper",
                    relevance_score=0.0,  # Will be scored later
                    claim_index=0,
                )
                sources.append(source)

        except httpx.TimeoutException:
            logger.debug("Semantic Scholar request timed out")
        except Exception as e:
            logger.debug(f"Semantic Scholar error: {e}")

        return sources

    async def _search_crossref(self, query: str) -> list[Source]:
        """Search CrossRef for papers and articles."""
        sources = []
        try:
            params = {
                "query": query,
                "rows": 5,
                "select": "DOI,title,author,published-print,published-online,type,URL",
            }

            headers = {
                "User-Agent": "Amplifier/1.0 (https://github.com/microsoft/amplifier; mailto:noreply@example.com)"
            }

            response = await self.client.get(CROSSREF_API, params=params, headers=headers)

            if response.status_code != 200:
                logger.debug(f"CrossRef returned {response.status_code}")
                return []

            data = response.json()
            items = data.get("message", {}).get("items", [])

            for item in items:
                # Extract title
                titles = item.get("title", [])
                title = titles[0] if titles else "Unknown"

                # Extract authors
                authors = []
                for author in item.get("author", []):
                    name_parts = []
                    if author.get("given"):
                        name_parts.append(author["given"])
                    if author.get("family"):
                        name_parts.append(author["family"])
                    if name_parts:
                        authors.append(" ".join(name_parts))

                # Extract year
                year = None
                published = item.get("published-print") or item.get("published-online")
                if published:
                    date_parts = published.get("date-parts", [[]])
                    if date_parts and date_parts[0]:
                        year = date_parts[0][0]

                # Map type
                item_type = item.get("type", "article")
                source_type = "paper" if item_type in ["journal-article", "proceedings-article"] else "article"

                source = Source(
                    title=title,
                    authors=authors[:5],
                    year=year,
                    doi=item.get("DOI"),
                    url=item.get("URL"),
                    source_type=source_type,
                    relevance_score=0.0,
                    claim_index=0,
                )
                sources.append(source)

        except httpx.TimeoutException:
            logger.debug("CrossRef request timed out")
        except Exception as e:
            logger.debug(f"CrossRef error: {e}")

        return sources

    async def _search_arxiv(self, query: str) -> list[Source]:
        """Search arXiv for preprints (good for CS, physics, math)."""
        sources = []
        try:
            # arXiv API uses search_query parameter with field prefixes
            # For general search, use 'all:' prefix
            params = {
                "search_query": f"all:{query}",
                "start": 0,
                "max_results": 5,
                "sortBy": "relevance",
            }

            response = await self.client.get(ARXIV_API, params=params)

            if response.status_code != 200:
                logger.debug(f"arXiv returned {response.status_code}")
                return []

            # Parse Atom/XML response
            root = ET.fromstring(response.text)

            # Define namespaces used by arXiv
            ns = {
                "atom": "http://www.w3.org/2005/Atom",
                "arxiv": "http://arxiv.org/schemas/atom",
            }

            for entry in root.findall("atom:entry", ns):
                # Extract title
                title_elem = entry.find("atom:title", ns)
                title = title_elem.text.strip() if title_elem is not None and title_elem.text else "Unknown"
                # Clean up multi-line titles
                title = " ".join(title.split())

                # Extract authors
                authors = []
                for author_elem in entry.findall("atom:author", ns):
                    name_elem = author_elem.find("atom:name", ns)
                    if name_elem is not None and name_elem.text:
                        authors.append(name_elem.text)

                # Extract year from published date
                published_elem = entry.find("atom:published", ns)
                year = None
                if published_elem is not None and published_elem.text:
                    # Format: 2023-01-15T00:00:00Z
                    year = int(published_elem.text[:4])

                # Extract arXiv ID and URL
                id_elem = entry.find("atom:id", ns)
                url = id_elem.text if id_elem is not None else None

                # Extract arXiv ID for DOI-like reference
                arxiv_id = None
                if url:
                    # URL format: http://arxiv.org/abs/2301.12345v1
                    arxiv_id = url.split("/abs/")[-1] if "/abs/" in url else None

                source = Source(
                    title=title,
                    authors=authors[:5],
                    year=year,
                    doi=f"arXiv:{arxiv_id}" if arxiv_id else None,
                    url=url,
                    source_type="preprint",
                    relevance_score=0.0,
                    claim_index=0,
                )
                sources.append(source)

        except httpx.TimeoutException:
            logger.debug("arXiv request timed out")
        except ET.ParseError as e:
            logger.debug(f"arXiv XML parse error: {e}")
        except Exception as e:
            logger.debug(f"arXiv error: {e}")

        return sources

    async def _search_cinii(self, query: str) -> list[Source]:
        """Search CiNii Research for Japanese academic papers."""
        sources = []
        try:
            # CiNii Research OpenSearch API
            params = {
                "q": query,
                "count": 5,
                "format": "atom",
                "lang": "ja",  # Prioritize Japanese results
            }

            response = await self.client.get(CINII_API, params=params)

            if response.status_code != 200:
                logger.debug(f"CiNii returned {response.status_code}")
                return []

            # Parse Atom/XML response
            root = ET.fromstring(response.text)

            # Define namespaces used by CiNii
            ns = {
                "atom": "http://www.w3.org/2005/Atom",
                "opensearch": "http://a9.com/-/spec/opensearch/1.1/",
                "dc": "http://purl.org/dc/elements/1.1/",
                "prism": "http://prismstandard.org/namespaces/basic/2.0/",
            }

            for entry in root.findall("atom:entry", ns):
                # Extract title
                title_elem = entry.find("atom:title", ns)
                title = title_elem.text.strip() if title_elem is not None and title_elem.text else "Unknown"

                # Extract authors from dc:creator elements
                authors = []
                for creator in entry.findall("dc:creator", ns):
                    if creator.text:
                        authors.append(creator.text.strip())

                # Extract year from prism:publicationDate or dc:date
                year = None
                pub_date = entry.find("prism:publicationDate", ns)
                if pub_date is None:
                    pub_date = entry.find("dc:date", ns)
                if pub_date is not None and pub_date.text:
                    # Format varies: YYYY, YYYY-MM, or YYYY-MM-DD
                    year_str = pub_date.text.strip()[:4]
                    if year_str.isdigit():
                        year = int(year_str)

                # Extract URL and ID
                url = None
                link_elem = entry.find("atom:link[@rel='alternate']", ns)
                if link_elem is not None:
                    url = link_elem.get("href")
                if url is None:
                    id_elem = entry.find("atom:id", ns)
                    if id_elem is not None and id_elem.text:
                        url = id_elem.text

                # Extract DOI if available
                doi = None
                for identifier in entry.findall("dc:identifier", ns):
                    if identifier.text and "doi.org" in identifier.text:
                        doi = identifier.text.split("doi.org/")[-1]
                        break

                source = Source(
                    title=title,
                    authors=authors[:5],
                    year=year,
                    doi=doi,
                    url=url,
                    source_type="paper",
                    relevance_score=0.0,
                    claim_index=0,
                )
                sources.append(source)

            logger.debug(f"CiNii found {len(sources)} sources for query: {query[:30]}...")

        except httpx.TimeoutException:
            logger.debug("CiNii request timed out")
        except ET.ParseError as e:
            logger.debug(f"CiNii XML parse error: {e}")
        except Exception as e:
            logger.debug(f"CiNii error: {e}")

        return sources

    def _score_and_dedupe(self, sources: list[Source], claim_text: str) -> list[Source]:
        """Score sources by relevance and remove duplicates.

        Uses CitationRules for domain-specific boosting and filtering.
        """
        if not sources:
            return []

        # Build a simple term set from the claim
        claim_terms = set(self._extract_search_terms(claim_text).lower().split())

        # Check if this is domain-specific content (based on term_mappings)
        has_domain_content = self.rules.has_domain_content(claim_text)

        # Score each source
        for source in sources:
            title_lower = source.title.lower()
            title_terms = set(title_lower.split())
            overlap = len(claim_terms & title_terms)

            # Base score from term overlap
            source.relevance_score = min(overlap / max(len(claim_terms), 1), 1.0)

            # Boost for having DOI (more authoritative)
            if source.doi:
                source.relevance_score = min(source.relevance_score + 0.1, 1.0)

            # Boost for recent papers
            if source.year and source.year >= 2015:
                source.relevance_score = min(source.relevance_score + 0.05, 1.0)

            # Domain-specific scoring when we have term mappings configured
            if has_domain_content and self.rules.term_mappings:
                # Big boost for titles containing domain terms (source language)
                source_terms_in_title = sum(1 for term in self.rules.term_mappings if term in title_lower)
                # Also check for translated terms (target language)
                target_terms_in_title = sum(
                    1
                    for term in self.rules.term_mappings.values()
                    if term in source.title  # Keep original case for non-Latin scripts
                )

                # Check for non-Latin characters in title (likely relevant for JP/CN/KR domains)
                has_non_latin = any("\u3040" <= c <= "\u9fff" for c in source.title)

                if source_terms_in_title > 0 or target_terms_in_title > 0:
                    boost = 0.4 + (0.1 * (source_terms_in_title + target_terms_in_title))
                    source.relevance_score = min(source.relevance_score + boost, 1.0)
                elif has_non_latin:
                    # Non-Latin title without known terms - still likely relevant for JP domains
                    source.relevance_score = min(source.relevance_score + 0.25, 1.0)

                # Check for CiNii sources (Japanese academic database)
                if source.url and "cir.nii.ac.jp" in source.url:
                    source.relevance_score = min(source.relevance_score + 0.2, 1.0)

                # Penalize obviously irrelevant titles using configured keywords
                if self.rules.irrelevant_keywords and any(kw in title_lower for kw in self.rules.irrelevant_keywords):
                    source.relevance_score = max(source.relevance_score - 0.7, 0.0)

                # Additional penalty for generic academic patterns
                if self.rules.generic_patterns and any(pat in title_lower for pat in self.rules.generic_patterns):
                    source.relevance_score = max(source.relevance_score - 0.5, 0.0)

        # Deduplicate by DOI and title similarity
        seen_dois: set[str] = set()
        seen_titles: set[str] = set()
        unique_sources: list[Source] = []

        for source in sorted(sources, key=lambda s: s.relevance_score, reverse=True):
            # Skip low relevance sources when domain rules are active
            # Use configured threshold (default 0.3, tea ceremony uses 0.45)
            if has_domain_content and source.relevance_score < self.rules.relevance_threshold:
                continue

            # Skip if we've seen this DOI
            if source.doi and source.doi in seen_dois:
                continue

            # Skip if title is too similar to one we've seen
            title_lower = source.title.lower()
            if any(self._title_similarity(title_lower, t) > 0.8 for t in seen_titles):
                continue

            unique_sources.append(source)
            if source.doi:
                seen_dois.add(source.doi)
            seen_titles.add(title_lower)

        return unique_sources

    def _title_similarity(self, t1: str, t2: str) -> float:
        """Simple title similarity based on word overlap."""
        words1 = set(t1.split())
        words2 = set(t2.split())
        if not words1 or not words2:
            return 0.0
        overlap = len(words1 & words2)
        return overlap / max(len(words1), len(words2))
