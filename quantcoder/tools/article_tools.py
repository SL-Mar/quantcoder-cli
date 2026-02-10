"""Tools for article search, download, and processing."""

import json
import requests
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List, Optional
from .base import Tool, ToolResult
from ..core.http_utils import (
    make_request_with_retry,
    cached_request,
    DEFAULT_TIMEOUT,
)


class SearchArticlesTool(Tool):
    """Tool for searching academic articles using arXiv API (open-access)."""

    ARXIV_NS = {'a': 'http://www.w3.org/2005/Atom'}

    @property
    def name(self) -> str:
        return "search_articles"

    @property
    def description(self) -> str:
        return "Search for open-access academic articles using arXiv API"

    def execute(self, query: str, max_results: int = 5) -> ToolResult:
        """
        Search for articles using arXiv API.

        Args:
            query: Search query string
            max_results: Maximum number of results to return

        Returns:
            ToolResult with list of articles
        """
        self.logger.info(f"Searching arXiv for: {query}")

        try:
            articles = self._search_arxiv(query, max_results=max_results)

            if articles is None:
                return ToolResult(
                    success=False,
                    error="arXiv rate limited. Wait a few minutes and try again."
                )

            if not articles:
                return ToolResult(
                    success=False,
                    error="No articles found on arXiv. Try broader terms or check your query."
                )

            # Save articles to cache
            cache_file = Path(self.config.home_dir) / "articles.json"
            cache_file.parent.mkdir(parents=True, exist_ok=True)

            with open(cache_file, 'w') as f:
                json.dump(articles, f, indent=4)

            return ToolResult(
                success=True,
                data=articles,
                message=f"Found {len(articles)} articles (arXiv open-access)"
            )

        except Exception as e:
            self.logger.error(f"Error searching articles: {e}")
            return ToolResult(success=False, error=str(e))

    def _search_arxiv(self, query: str, max_results: int = 5) -> List[Dict]:
        """Search arXiv API for articles, scoped to finance/CS categories."""
        import time

        # Build query: treat quoted strings as exact phrases, split rest into AND terms
        raw = query.strip()
        # Keep hyphenated terms as-is (arXiv handles them), split on spaces
        search_terms = raw.split()
        terms_query = " AND ".join(f"all:{t}" for t in search_terms)
        # Restrict to quantitative finance, computational finance, stats, CS
        cat_filter = (
            "cat:q-fin.* OR cat:stat.ML OR cat:cs.CE OR cat:cs.LG OR cat:econ.*"
        )
        arxiv_query = f"({terms_query}) AND ({cat_filter})"

        max_attempts = 3
        for attempt in range(max_attempts):
            try:
                response = make_request_with_retry(
                    url="https://export.arxiv.org/api/query",
                    method="GET",
                    params={
                        "search_query": arxiv_query,
                        "start": 0,
                        "max_results": max_results,
                        "sortBy": "relevance",
                        "sortOrder": "descending",
                    },
                    timeout=30,
                    retries=2,
                    backoff_factor=1.0,
                )

                if not response.content:
                    self.logger.error("Empty response from arXiv API")
                    return []

                # Handle rate limiting (429) and other HTTP errors
                if response.status_code == 429:
                    wait = 5 * (attempt + 1)
                    self.logger.warning(f"arXiv rate limited (429), waiting {wait}s (attempt {attempt + 1}/{max_attempts})")
                    time.sleep(wait)
                    continue

                if response.status_code != 200:
                    self.logger.error(f"arXiv returned HTTP {response.status_code}: {response.text[:200]}")
                    if attempt < max_attempts - 1:
                        time.sleep(3)
                        continue
                    return None  # signal rate limit / server error

                root = ET.fromstring(response.content)
                entries = root.findall('a:entry', self.ARXIV_NS)

                articles = []
                for entry in entries:
                    arxiv_id = entry.find('a:id', self.ARXIV_NS).text.split('/abs/')[-1]
                    title = ' '.join(entry.find('a:title', self.ARXIV_NS).text.strip().split())
                    authors = self._format_authors(entry.findall('a:author', self.ARXIV_NS))
                    published = entry.find('a:published', self.ARXIV_NS).text[:4]
                    summary = ' '.join(entry.find('a:summary', self.ARXIV_NS).text.strip().split())

                    # Get categories
                    categories = [
                        c.get('term', '')
                        for c in entry.findall('a:category', self.ARXIV_NS)
                    ]

                    article = {
                        'title': title,
                        'authors': authors,
                        'published': published,
                        'DOI': f"arXiv:{arxiv_id}",
                        'URL': f"https://arxiv.org/pdf/{arxiv_id}",
                        'abstract_url': f"https://arxiv.org/abs/{arxiv_id}",
                        'categories': categories,
                        'summary': summary[:300],
                    }
                    articles.append(article)

                return articles

            except ET.ParseError as e:
                self.logger.warning(f"Failed to parse arXiv response (attempt {attempt + 1}/{max_attempts}): {e}")
                if attempt < max_attempts - 1:
                    time.sleep(5)
                    continue
                return None
            except Exception as e:
                self.logger.error(f"arXiv API request failed: {e}")
                if attempt < max_attempts - 1:
                    time.sleep(3)
                    continue
                return None

        return None  # all attempts exhausted

    def _format_authors(self, author_elements) -> str:
        """Format author list from arXiv XML elements."""
        if not author_elements:
            return "Unknown"
        names = [
            a.find('a:name', self.ARXIV_NS).text
            for a in author_elements[:3]
            if a.find('a:name', self.ARXIV_NS) is not None
        ]
        result = ", ".join(names)
        if len(author_elements) > 3:
            result += f" (+{len(author_elements) - 3} more)"
        return result


class DownloadArticleTool(Tool):
    """Tool for downloading article PDFs."""

    @property
    def name(self) -> str:
        return "download_article"

    @property
    def description(self) -> str:
        return "Download an article PDF by ID from cached search results"

    def execute(self, article_id: int) -> ToolResult:
        """
        Download an article PDF.

        Args:
            article_id: Article ID from search results (1-indexed)

        Returns:
            ToolResult with download path
        """
        self.logger.info(f"Downloading article {article_id}")

        try:
            # Load cached articles
            cache_file = Path(self.config.home_dir) / "articles.json"
            if not cache_file.exists():
                return ToolResult(
                    success=False,
                    error="No articles found. Please search first."
                )

            with open(cache_file, 'r') as f:
                articles = json.load(f)

            if article_id < 1 or article_id > len(articles):
                return ToolResult(
                    success=False,
                    error=f"Article ID {article_id} not found. Valid range: 1-{len(articles)}"
                )

            article = articles[article_id - 1]

            # Create downloads directory
            downloads_dir = Path(self.config.tools.downloads_dir)
            downloads_dir.mkdir(parents=True, exist_ok=True)

            # Define save path
            filename = f"article_{article_id}.pdf"
            save_path = downloads_dir / filename

            # Attempt to download
            doi = article.get("DOI")
            success = self._download_pdf(article["URL"], save_path, doi=doi)

            if success:
                return ToolResult(
                    success=True,
                    data=str(save_path),
                    message=f"Article downloaded to {save_path}"
                )
            else:
                doi = article.get("DOI", "")
                url = article.get("URL", "")
                hint = (
                    f"PDF is paywalled or not directly accessible.\n"
                    f"  DOI: {doi}\n"
                    f"  URL: {url}\n"
                    f"  Try: 1) Search for the title on arxiv.org or scholar.google.com\n"
                    f"       2) Place a PDF manually in '{downloads_dir}/article_{article_id}.pdf'\n"
                    f"       3) Search with open-access terms: 'quantcoder search \"{article['title'][:40]}... arXiv\"'"
                )
                return ToolResult(
                    success=False,
                    error=hint,
                    data={"url": url, "doi": doi, "can_open_browser": True}
                )

        except Exception as e:
            self.logger.error(f"Error downloading article: {e}")
            return ToolResult(success=False, error=str(e))

    def _download_pdf(self, url: str, save_path: Path, doi: Optional[str] = None) -> bool:
        """Attempt to download PDF, trying open-access sources first if DOI available."""
        # For arXiv URLs, download directly (already open-access)
        if 'arxiv.org' in url:
            return self._fetch_pdf(url, save_path)

        # Try open-access sources via Unpaywall API if we have a DOI
        if doi:
            oa_url = self._find_open_access_url(doi)
            if oa_url:
                self.logger.info(f"Found open-access PDF via Unpaywall: {oa_url}")
                if self._fetch_pdf(oa_url, save_path):
                    return True

        # Fallback: try the publisher URL directly
        return self._fetch_pdf(url, save_path)

    def _find_open_access_url(self, doi: str) -> Optional[str]:
        """Check Unpaywall for a free open-access PDF URL."""
        try:
            unpaywall_url = f"https://api.unpaywall.org/v2/{doi}"
            response = make_request_with_retry(
                url=unpaywall_url,
                method="GET",
                params={"email": "quantcoder@example.com"},
                timeout=15,
                retries=2,
                backoff_factor=0.5,
            )
            if response.status_code == 200:
                data = response.json()
                best_oa = data.get("best_oa_location")
                if best_oa and best_oa.get("url_for_pdf"):
                    return best_oa["url_for_pdf"]
        except Exception as e:
            self.logger.debug(f"Unpaywall lookup failed for {doi}: {e}")
        return None

    def _fetch_pdf(self, url: str, save_path: Path) -> bool:
        """Fetch a PDF from a URL and save it."""
        try:
            response = make_request_with_retry(
                url=url,
                method="GET",
                timeout=60,
                retries=3,
                backoff_factor=1.0,
            )
            response.raise_for_status()

            content_type = response.headers.get('Content-Type', '')
            is_pdf = 'application/pdf' in content_type or response.content[:5] == b'%PDF-'
            if is_pdf:
                with open(save_path, 'wb') as f:
                    f.write(response.content)
                return True

        except requests.exceptions.RequestException as e:
            self.logger.debug(f"PDF fetch failed for {url}: {e}")

        return False


class SummarizeArticleTool(Tool):
    """Tool for summarizing downloaded articles."""

    @property
    def name(self) -> str:
        return "summarize_article"

    @property
    def description(self) -> str:
        return "Extract and summarize trading strategy from article PDF(s)"

    def execute(self, article_ids: List[int]) -> ToolResult:
        """
        Summarize one or more articles.

        If multiple articles are provided, also creates a consolidated summary.

        Args:
            article_ids: List of article IDs from search results (1-indexed)

        Returns:
            ToolResult with summary data including consolidated summary ID if multiple
        """
        from ..core.processor import ArticleProcessor
        from ..core.summary_store import SummaryStore, IndividualSummary

        # Ensure it's a list
        if isinstance(article_ids, int):
            article_ids = [article_ids]

        self.logger.info(f"Summarizing articles: {article_ids}")

        try:
            # Initialize summary store
            store = SummaryStore(self.config.home_dir)

            # Load articles metadata
            cache_file = Path(self.config.home_dir) / "articles.json"
            if not cache_file.exists():
                return ToolResult(
                    success=False,
                    error="No articles found. Please search first."
                )

            with open(cache_file, 'r') as f:
                articles = json.load(f)

            # Process each article
            processor = ArticleProcessor(self.config)
            individual_summaries = []
            summary_ids = []

            for article_id in article_ids:
                # Validate article ID
                if article_id < 1 or article_id > len(articles):
                    return ToolResult(
                        success=False,
                        error=f"Article ID {article_id} not found. Valid range: 1-{len(articles)}"
                    )

                # Find the article file
                filepath = Path(self.config.tools.downloads_dir) / f"article_{article_id}.pdf"

                if not filepath.exists():
                    return ToolResult(
                        success=False,
                        error=f"Article {article_id} not downloaded. Please download it first."
                    )

                # Get article metadata
                article_meta = articles[article_id - 1]

                # Process the article (two-pass pipeline with legacy fallback)
                summary_text = processor.generate_two_pass_summary(str(filepath))

                if not summary_text:
                    self.logger.warning(f"Failed to generate summary for article {article_id}")
                    continue

                # Parse summary to extract structured data
                parsed = self._parse_summary(summary_text)

                # Create individual summary object
                individual = IndividualSummary(
                    article_id=article_id,
                    title=article_meta.get('title', 'Unknown'),
                    authors=article_meta.get('authors', 'Unknown'),
                    url=article_meta.get('URL', ''),
                    strategy_type=parsed.get('strategy_type', 'unknown'),
                    key_concepts=parsed.get('key_concepts', []),
                    indicators=parsed.get('indicators', []),
                    risk_approach=parsed.get('risk_approach', ''),
                    summary_text=summary_text
                )

                # Save to store
                summary_id = store.save_individual(individual)
                summary_ids.append(summary_id)
                individual_summaries.append(individual)

                self.logger.info(f"Created summary #{summary_id} for article {article_id}")

            if not individual_summaries:
                return ToolResult(
                    success=False,
                    error="Failed to generate any summaries"
                )

            result_data = {
                "individual_summary_ids": summary_ids,
                "summaries": [s.to_dict() for s in individual_summaries]
            }

            # If multiple articles, create consolidated summary
            consolidated_id = None
            if len(individual_summaries) > 1:
                consolidated_id = self._create_consolidated_summary(
                    store, individual_summaries, articles
                )
                result_data["consolidated_summary_id"] = consolidated_id

            message = f"Created summaries: {summary_ids}"
            if consolidated_id:
                message += f"\nConsolidated summary created: #{consolidated_id} (from articles {article_ids})"

            return ToolResult(
                success=True,
                data=result_data,
                message=message
            )

        except Exception as e:
            self.logger.error(f"Error summarizing articles: {e}")
            return ToolResult(success=False, error=str(e))

    def _parse_summary(self, summary_text: str) -> Dict:
        """Parse summary text to extract structured information."""
        # Simple extraction - can be enhanced with LLM
        parsed = {
            "strategy_type": "unknown",
            "key_concepts": [],
            "indicators": [],
            "risk_approach": ""
        }

        text_lower = summary_text.lower()

        # Detect strategy type
        if "momentum" in text_lower:
            parsed["strategy_type"] = "momentum"
        elif "mean reversion" in text_lower or "mean-reversion" in text_lower:
            parsed["strategy_type"] = "mean_reversion"
        elif "arbitrage" in text_lower:
            parsed["strategy_type"] = "arbitrage"
        elif "factor" in text_lower:
            parsed["strategy_type"] = "factor"
        elif "machine learning" in text_lower or "ml" in text_lower:
            parsed["strategy_type"] = "machine_learning"

        # Detect indicators
        indicator_keywords = [
            "SMA", "EMA", "RSI", "MACD", "Bollinger", "ATR",
            "moving average", "relative strength", "volatility"
        ]
        for ind in indicator_keywords:
            if ind.lower() in text_lower:
                parsed["indicators"].append(ind)

        return parsed

    def _create_consolidated_summary(
        self,
        store,
        individual_summaries: List,
        articles: List[Dict]
    ) -> int:
        """Create a consolidated summary from multiple individual summaries."""
        from ..core.summary_store import ConsolidatedSummary
        from ..core.llm import get_llm_provider

        # Build references
        references = []
        contributions = {}
        all_concepts = []
        all_indicators = []

        for summary in individual_summaries:
            references.append({
                "id": summary.article_id,
                "title": summary.title,
                "contribution": summary.strategy_type
            })
            contributions[summary.article_id] = summary.strategy_type
            all_concepts.extend(summary.key_concepts)
            all_indicators.extend(summary.indicators)

        # Determine merged strategy type
        strategy_types = [s.strategy_type for s in individual_summaries]
        if len(set(strategy_types)) == 1:
            merged_type = strategy_types[0]
        else:
            merged_type = "hybrid"

        # Generate consolidated description using LLM
        try:
            llm = get_llm_provider(self.config)
            merged_description = self._generate_consolidated_description(
                llm, individual_summaries
            )
        except Exception as e:
            self.logger.warning(f"LLM consolidation failed: {e}, using template")
            merged_description = self._generate_template_description(individual_summaries)

        # Create consolidated summary
        consolidated = ConsolidatedSummary(
            summary_id=0,  # Will be assigned by store
            source_article_ids=[s.article_id for s in individual_summaries],
            references=references,
            merged_strategy_type=merged_type,
            merged_description=merged_description,
            contributions_by_article=contributions,
            key_concepts=list(set(all_concepts)),
            indicators=list(set(all_indicators)),
            risk_approach="Combined risk management approach"
        )

        return store.save_consolidated(consolidated)

    def _generate_consolidated_description(self, llm, summaries: List) -> str:
        """Generate consolidated description using LLM."""
        summaries_text = "\n\n".join([
            f"Article {s.article_id} ({s.title}):\n{s.summary_text}"
            for s in summaries
        ])

        prompt = f"""Consolidate these trading strategy summaries into a single coherent strategy description.
Identify what each article contributes and how they can be combined.

{summaries_text}

Write a 2-3 paragraph consolidated strategy description that:
1. Explains the combined approach
2. Notes what each source article contributes
3. Describes how the concepts work together

Be concise and technical."""

        response = llm.generate(prompt, max_tokens=500)
        return response.strip()

    def _generate_template_description(self, summaries: List) -> str:
        """Generate template-based consolidated description."""
        parts = []
        for s in summaries:
            parts.append(f"From article {s.article_id} ({s.title}): {s.strategy_type} approach")

        return f"""This consolidated strategy combines concepts from {len(summaries)} research articles:

{chr(10).join('- ' + p for p in parts)}

The combined approach integrates multiple trading methodologies into a unified framework."""
