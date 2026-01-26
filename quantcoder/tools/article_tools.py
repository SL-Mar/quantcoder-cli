"""Tools for article search, download, and processing."""

import os
import json
import asyncio
import aiohttp
import webbrowser
from pathlib import Path
from typing import Dict, List, Optional
from .base import Tool, ToolResult, get_safe_path, PathSecurityError

# Maximum allowed article ID to prevent DoS via huge IDs
MAX_ARTICLE_ID = 10000


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
        """Search CrossRef API for articles (sync wrapper)."""
        try:
            return asyncio.get_event_loop().run_until_complete(
                self._search_crossref_async(query, rows)
            )
        except RuntimeError:
            # No event loop running, create a new one
            return asyncio.run(self._search_crossref_async(query, rows))

    async def _search_crossref_async(self, query: str, rows: int = 5) -> List[Dict]:
        """Search CrossRef API for articles using async aiohttp."""
        api_url = "https://api.crossref.org/works"
        params = {
            "query": query,
            "rows": rows,
            "select": "DOI,title,author,published-print,URL"
        }
        headers = {
            "User-Agent": "QuantCoder/2.0 (mailto:smr.laignel@gmail.com)"
        }

        try:
            timeout = aiohttp.ClientTimeout(total=10)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(api_url, params=params, headers=headers) as response:
                    response.raise_for_status()
                    data = await response.json()

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

        except aiohttp.ClientError as e:
            self.logger.error(f"CrossRef API request failed: {e}")
            return []
        except asyncio.TimeoutError:
            self.logger.error("CrossRef API request timed out")
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
            # Validate article_id bounds
            if not isinstance(article_id, int) or article_id < 1 or article_id > MAX_ARTICLE_ID:
                return ToolResult(
                    success=False,
                    error=f"Invalid article ID. Must be between 1 and {MAX_ARTICLE_ID}"
                )

            # Load cached articles
            cache_file = Path(self.config.home_dir) / "articles.json"
            if not cache_file.exists():
                return ToolResult(
                    success=False,
                    error="No articles found. Please search first."
                )

            with open(cache_file, 'r') as f:
                articles = json.load(f)

            if article_id > len(articles):
                return ToolResult(
                    success=False,
                    error=f"Article ID {article_id} not found. Valid range: 1-{len(articles)}"
                )

            article = articles[article_id - 1]

            # Create downloads directory with path validation
            # Resolve the downloads_dir relative to current working directory
            base_dir = Path.cwd()
            try:
                save_path = get_safe_path(
                    base_dir,
                    self.config.tools.downloads_dir,
                    f"article_{article_id}.pdf",
                    create_parents=True
                )
            except PathSecurityError as e:
                self.logger.error(f"Path security error: {e}")
                return ToolResult(
                    success=False,
                    error="Invalid downloads directory configuration"
                )

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

        except PathSecurityError as e:
            self.logger.error(f"Path security error: {e}")
            return ToolResult(success=False, error="Path security violation")
        except Exception as e:
            self.logger.error(f"Error downloading article: {e}")
            return ToolResult(success=False, error=str(e))

    def _download_pdf(self, url: str, save_path: Path, doi: Optional[str] = None) -> bool:
        """Attempt to download PDF from URL (sync wrapper)."""
        try:
            return asyncio.get_event_loop().run_until_complete(
                self._download_pdf_async(url, save_path, doi)
            )
        except RuntimeError:
            # No event loop running, create a new one
            return asyncio.run(self._download_pdf_async(url, save_path, doi))

    async def _download_pdf_async(self, url: str, save_path: Path, doi: Optional[str] = None) -> bool:
        """Attempt to download PDF from URL using async aiohttp."""
        headers = {
            "User-Agent": "QuantCoder/2.0 (mailto:smr.laignel@gmail.com)"
        }

        try:
            # First check Content-Type with HEAD request to avoid downloading non-PDFs
            timeout = aiohttp.ClientTimeout(total=30)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                # Check content type before downloading
                async with session.head(url, headers=headers, allow_redirects=True) as head_response:
                    content_type = head_response.headers.get('Content-Type', '')
                    if 'application/pdf' not in content_type:
                        self.logger.debug(f"URL does not point to PDF (Content-Type: {content_type})")
                        return False

                # Download the PDF
                async with session.get(url, headers=headers, allow_redirects=True) as response:
                    response.raise_for_status()

                    if 'application/pdf' in response.headers.get('Content-Type', ''):
                        content = await response.read()
                        with open(save_path, 'wb') as f:
                            f.write(content)
                        return True

        except aiohttp.ClientError as e:
            self.logger.error(f"Failed to download PDF: {e}")
        except asyncio.TimeoutError:
            self.logger.error("PDF download timed out")

        return False


class SummarizeArticleTool(Tool):
    """Tool for summarizing downloaded articles."""

    @property
    def name(self) -> str:
        return "summarize_article"

    @property
    def description(self) -> str:
        return "Extract and summarize trading strategy from an article PDF"

    def execute(self, article_id: int) -> ToolResult:
        """
        Summarize an article.

        Args:
            article_id: Article ID from search results (1-indexed)

        Returns:
            ToolResult with summary text
        """
        from ..core.processor import ArticleProcessor

        self.logger.info(f"Summarizing article {article_id}")

        try:
            # Validate article_id bounds
            if not isinstance(article_id, int) or article_id < 1 or article_id > MAX_ARTICLE_ID:
                return ToolResult(
                    success=False,
                    error=f"Invalid article ID. Must be between 1 and {MAX_ARTICLE_ID}"
                )

            # Find the article file with path validation
            base_dir = Path.cwd()
            try:
                filepath = get_safe_path(
                    base_dir,
                    self.config.tools.downloads_dir,
                    f"article_{article_id}.pdf"
                )
            except PathSecurityError as e:
                self.logger.error(f"Path security error: {e}")
                return ToolResult(
                    success=False,
                    error="Invalid downloads directory configuration"
                )

            if not filepath.exists():
                return ToolResult(
                    success=False,
                    error=f"Article not downloaded. Please download article {article_id} first."
                )

            # Process the article
            processor = ArticleProcessor(self.config)
            extracted_data = processor.extract_structure(str(filepath))

            if not extracted_data:
                return ToolResult(
                    success=False,
                    error="Failed to extract data from the article"
                )

            # Generate summary
            summary = processor.generate_summary(extracted_data)

            if not summary:
                return ToolResult(
                    success=False,
                    error="Failed to generate summary"
                )

            # Save summary with path validation
            try:
                summary_path = get_safe_path(
                    base_dir,
                    self.config.tools.downloads_dir,
                    f"article_{article_id}_summary.txt",
                    create_parents=True
                )
            except PathSecurityError as e:
                self.logger.error(f"Path security error: {e}")
                return ToolResult(
                    success=False,
                    error="Invalid downloads directory configuration"
                )

            with open(summary_path, 'w', encoding='utf-8') as f:
                f.write(summary)

            return ToolResult(
                success=True,
                data={"summary": summary, "path": str(summary_path)},
                message=f"Summary saved to {summary_path}"
            )

        except PathSecurityError as e:
            self.logger.error(f"Path security error: {e}")
            return ToolResult(success=False, error="Path security violation")
        except Exception as e:
            self.logger.error(f"Error summarizing article: {e}")
            return ToolResult(success=False, error=str(e))
