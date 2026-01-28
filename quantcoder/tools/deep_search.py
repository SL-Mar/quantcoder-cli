"""Deep search using Tavily API for high-quality research discovery."""

import os
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

import requests

from .base import Tool, ToolResult

logger = logging.getLogger(__name__)


@dataclass
class SearchResult:
    """A single search result from Tavily."""
    title: str
    url: str
    content: str  # Extracted content/snippet
    score: float  # Relevance score
    published_date: Optional[str] = None

    def to_dict(self) -> Dict:
        return {
            "title": self.title,
            "url": self.url,
            "content": self.content,
            "score": self.score,
            "published_date": self.published_date,
        }


class TavilyClient:
    """Client for Tavily Search API."""

    BASE_URL = "https://api.tavily.com"

    def __init__(self, api_key: Optional[str] = None):
        """Initialize Tavily client.

        Args:
            api_key: Tavily API key. Falls back to TAVILY_API_KEY env var.
        """
        self.api_key = api_key or os.getenv("TAVILY_API_KEY")

        if not self.api_key:
            logger.warning("Tavily API key not configured. Set TAVILY_API_KEY environment variable.")

    def is_configured(self) -> bool:
        """Check if client is properly configured."""
        return bool(self.api_key)

    def search(
        self,
        query: str,
        search_depth: str = "advanced",
        max_results: int = 10,
        include_domains: Optional[List[str]] = None,
        exclude_domains: Optional[List[str]] = None,
        include_answer: bool = False,
        include_raw_content: bool = False,
    ) -> List[SearchResult]:
        """Search using Tavily API.

        Args:
            query: Search query
            search_depth: "basic" or "advanced" (more thorough)
            max_results: Maximum number of results
            include_domains: Only include results from these domains
            exclude_domains: Exclude results from these domains
            include_answer: Include AI-generated answer summary
            include_raw_content: Include full page content

        Returns:
            List of SearchResult objects
        """
        if not self.api_key:
            logger.error("Tavily API key not configured")
            return []

        payload = {
            "api_key": self.api_key,
            "query": query,
            "search_depth": search_depth,
            "max_results": max_results,
            "include_answer": include_answer,
            "include_raw_content": include_raw_content,
        }

        if include_domains:
            payload["include_domains"] = include_domains
        if exclude_domains:
            payload["exclude_domains"] = exclude_domains

        try:
            response = requests.post(
                f"{self.BASE_URL}/search",
                json=payload,
                timeout=30
            )
            response.raise_for_status()
            data = response.json()

            results = []
            for item in data.get("results", []):
                results.append(SearchResult(
                    title=item.get("title", ""),
                    url=item.get("url", ""),
                    content=item.get("content", ""),
                    score=item.get("score", 0.0),
                    published_date=item.get("published_date"),
                ))

            return results

        except requests.exceptions.RequestException as e:
            logger.error(f"Tavily search failed: {e}")
            return []

    def search_research_papers(
        self,
        query: str,
        max_results: int = 10,
    ) -> List[SearchResult]:
        """Search specifically for research papers and academic content.

        Args:
            query: Search query
            max_results: Maximum number of results

        Returns:
            List of SearchResult objects
        """
        # Enhance query for academic/research content
        enhanced_query = f"{query} research paper quantitative trading strategy backtest"

        # Focus on academic and research domains
        include_domains = [
            "arxiv.org",
            "ssrn.com",
            "papers.ssrn.com",
            "scholar.google.com",
            "researchgate.net",
            "sciencedirect.com",
            "springer.com",
            "wiley.com",
            "tandfonline.com",
            "jstor.org",
            "nber.org",
        ]

        return self.search(
            query=enhanced_query,
            search_depth="advanced",
            max_results=max_results,
            include_domains=include_domains,
        )


class DeepSearchTool(Tool):
    """Tool for deep research paper discovery using Tavily."""

    @property
    def name(self) -> str:
        return "deep_search"

    @property
    def description(self) -> str:
        return "Deep semantic search for research papers using Tavily API"

    def execute(
        self,
        query: str,
        max_results: int = 10,
        filter_relevance: bool = True,
        min_relevance_score: float = 0.5,
    ) -> ToolResult:
        """Execute deep search for research papers.

        Args:
            query: Search query (e.g., "momentum trading strategy")
            max_results: Maximum number of results to return
            filter_relevance: Use LLM to filter for implementable strategies
            min_relevance_score: Minimum Tavily relevance score (0-1)

        Returns:
            ToolResult with list of relevant papers
        """
        self.logger.info(f"Deep searching for: {query}")

        # Check Tavily configuration
        tavily = TavilyClient()
        if not tavily.is_configured():
            return ToolResult(
                success=False,
                error="Tavily API key not configured. Set TAVILY_API_KEY in ~/.quantcoder/.env"
            )

        try:
            # Search using Tavily
            results = tavily.search_research_papers(query, max_results=max_results * 2)

            if not results:
                return ToolResult(
                    success=False,
                    error="No results found. Try a different query."
                )

            # Filter by minimum relevance score
            results = [r for r in results if r.score >= min_relevance_score]

            # Optionally filter for implementable strategies using LLM
            if filter_relevance and results:
                results = self._filter_for_implementable(results)

            # Limit to requested max
            results = results[:max_results]

            if not results:
                return ToolResult(
                    success=False,
                    error="No implementable trading strategies found in search results."
                )

            # Convert to article format compatible with existing workflow
            articles = self._convert_to_articles(results)

            # Save to articles.json for compatibility with download/summarize
            self._save_articles_cache(articles)

            return ToolResult(
                success=True,
                data=articles,
                message=f"Found {len(articles)} relevant papers via deep search"
            )

        except Exception as e:
            self.logger.error(f"Deep search failed: {e}")
            return ToolResult(success=False, error=str(e))

    def _filter_for_implementable(self, results: List[SearchResult]) -> List[SearchResult]:
        """Filter results for papers with implementable trading strategies.

        Uses LLM to analyze content and determine if the paper contains
        a backtestable quantitative trading strategy.
        """
        try:
            from ..core.llm import get_llm_provider
            llm = get_llm_provider(self.config)
        except Exception as e:
            self.logger.warning(f"LLM not available for filtering: {e}")
            return results

        filtered = []

        for result in results:
            # Build prompt for relevance check
            prompt = f"""Analyze this search result and determine if it describes an IMPLEMENTABLE quantitative trading strategy.

Title: {result.title}
Content: {result.content[:1000]}

Answer with ONLY "YES" or "NO":
- YES if the paper describes a specific, backtestable trading strategy with clear rules
- NO if it's theoretical, survey-only, or doesn't describe a concrete strategy

Answer:"""

            try:
                response = llm.generate(prompt, max_tokens=10)
                is_relevant = "YES" in response.upper()

                if is_relevant:
                    filtered.append(result)
                    self.logger.debug(f"Kept: {result.title}")
                else:
                    self.logger.debug(f"Filtered out: {result.title}")

            except Exception as e:
                self.logger.warning(f"LLM filter failed for {result.title}: {e}")
                # Keep result if LLM fails
                filtered.append(result)

        return filtered

    def _convert_to_articles(self, results: List[SearchResult]) -> List[Dict]:
        """Convert SearchResults to article format compatible with existing workflow."""
        articles = []

        for result in results:
            # Extract DOI if present in URL
            doi = ""
            if "doi.org" in result.url:
                doi = result.url.split("doi.org/")[-1]
            elif "arxiv.org" in result.url:
                # Extract arxiv ID
                doi = result.url.split("/")[-1]

            article = {
                "title": result.title,
                "authors": "Unknown",  # Tavily doesn't always provide authors
                "published": result.published_date or "",
                "DOI": doi,
                "URL": result.url,
                "abstract": result.content,  # Use content as abstract
                "relevance_score": result.score,
                "source": "tavily_deep_search",
            }
            articles.append(article)

        return articles

    def _save_articles_cache(self, articles: List[Dict]):
        """Save articles to cache file for compatibility with download/summarize."""
        import json
        from pathlib import Path

        cache_file = Path(self.config.home_dir) / "articles.json"
        cache_file.parent.mkdir(parents=True, exist_ok=True)

        with open(cache_file, 'w') as f:
            json.dump(articles, f, indent=4)

        self.logger.info(f"Saved {len(articles)} articles to cache")
