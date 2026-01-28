"""Tools for article search, download, and processing."""

import json
import requests
from pathlib import Path
from typing import Dict, List, Optional
from .base import Tool, ToolResult
from ..core.http_utils import (
    make_request_with_retry,
    cached_request,
    DEFAULT_TIMEOUT,
)


class SearchArticlesTool(Tool):
    """Tool for searching academic articles using CrossRef API."""

    @property
    def name(self) -> str:
        return "search_articles"

    @property
    def description(self) -> str:
        return "Search for academic articles using CrossRef API"

    def execute(self, query: str, max_results: int = 5) -> ToolResult:
        """
        Search for articles using CrossRef API.

        Args:
            query: Search query string
            max_results: Maximum number of results to return

        Returns:
            ToolResult with list of articles
        """
        self.logger.info(f"Searching for articles: {query}")

        try:
            articles = self._search_crossref(query, rows=max_results)

            if not articles:
                return ToolResult(
                    success=False,
                    error="No articles found or an error occurred during the search"
                )

            # Save articles to cache
            cache_file = Path(self.config.home_dir) / "articles.json"
            cache_file.parent.mkdir(parents=True, exist_ok=True)

            with open(cache_file, 'w') as f:
                json.dump(articles, f, indent=4)

            return ToolResult(
                success=True,
                data=articles,
                message=f"Found {len(articles)} articles"
            )

        except Exception as e:
            self.logger.error(f"Error searching articles: {e}")
            return ToolResult(success=False, error=str(e))

    def _search_crossref(self, query: str, rows: int = 5) -> List[Dict]:
        """Search CrossRef API for articles with retry and caching support."""
        api_url = "https://api.crossref.org/works"
        params = {
            "query": query,
            "rows": rows,
            "select": "DOI,title,author,published-print,URL"
        }

        try:
            # Use cached_request for automatic retry and caching
            data = cached_request(
                url=api_url,
                params=params,
                timeout=DEFAULT_TIMEOUT,
                use_cache=True,
                cache_ttl=1800,  # 30 minutes cache for search results
            )

            if not data:
                self.logger.error("CrossRef API request failed after retries")
                return []

            articles = []
            for item in data.get('message', {}).get('items', []):
                article = {
                    'title': item.get('title', ['No title'])[0],
                    'authors': self._format_authors(item.get('author', [])),
                    'published': self._format_date(item.get('published-print')),
                    'DOI': item.get('DOI', ''),
                    'URL': item.get('URL', '')
                }
                articles.append(article)

            return articles

        except Exception as e:
            self.logger.error(f"CrossRef API request failed: {e}")
            return []

    def _format_authors(self, authors: List[Dict]) -> str:
        """Format author list."""
        if not authors:
            return "Unknown"
        author_names = [
            f"{a.get('given', '')} {a.get('family', '')}".strip()
            for a in authors[:3]
        ]
        return ", ".join(author_names)

    def _format_date(self, date_parts: Optional[Dict]) -> str:
        """Format publication date."""
        if not date_parts or 'date-parts' not in date_parts:
            return ""
        parts = date_parts['date-parts'][0]
        if len(parts) > 0:
            return str(parts[0])
        return ""


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
                # Offer to open in browser
                return ToolResult(
                    success=False,
                    error="Failed to download PDF",
                    data={"url": article["URL"], "can_open_browser": True}
                )

        except Exception as e:
            self.logger.error(f"Error downloading article: {e}")
            return ToolResult(success=False, error=str(e))

    def _download_pdf(self, url: str, save_path: Path, doi: Optional[str] = None) -> bool:
        """Attempt to download PDF from URL with retry support."""
        try:
            # Use make_request_with_retry for automatic retry on failure
            response = make_request_with_retry(
                url=url,
                method="GET",
                timeout=60,  # Longer timeout for PDF downloads
                retries=3,
                backoff_factor=1.0,  # 1s, 2s, 4s backoff
            )
            response.raise_for_status()

            if 'application/pdf' in response.headers.get('Content-Type', ''):
                with open(save_path, 'wb') as f:
                    f.write(response.content)
                return True

        except requests.exceptions.RequestException as e:
            self.logger.error(f"Failed to download PDF after retries: {e}")

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

                # Process the article
                extracted_data = processor.extract_structure(str(filepath))

                if not extracted_data:
                    self.logger.warning(f"Failed to extract data from article {article_id}")
                    continue

                # Generate summary
                summary_text = processor.generate_summary(extracted_data)

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
