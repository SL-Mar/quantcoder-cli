"""Tests for deep search using Tavily."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

from quantcoder.tools.deep_search import (
    TavilyClient,
    DeepSearchTool,
    SearchResult,
)


class TestTavilyClient:
    """Tests for TavilyClient."""

    def test_is_configured_without_key(self):
        """Test configuration check without API key."""
        with patch.dict('os.environ', {}, clear=True):
            client = TavilyClient(api_key=None)
            assert not client.is_configured()

    def test_is_configured_with_key(self):
        """Test configuration check with API key."""
        client = TavilyClient(api_key="test-key")
        assert client.is_configured()

    def test_is_configured_from_env(self):
        """Test configuration from environment variable."""
        with patch.dict('os.environ', {'TAVILY_API_KEY': 'env-key'}):
            client = TavilyClient()
            assert client.is_configured()
            assert client.api_key == 'env-key'

    @patch('requests.post')
    def test_search_success(self, mock_post):
        """Test successful search."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "results": [
                {
                    "title": "Momentum Trading Strategies",
                    "url": "https://arxiv.org/abs/1234.5678",
                    "content": "This paper presents a momentum strategy...",
                    "score": 0.85,
                    "published_date": "2024-01-15",
                }
            ]
        }
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response

        client = TavilyClient(api_key="test-key")
        results = client.search("momentum trading")

        assert len(results) == 1
        assert results[0].title == "Momentum Trading Strategies"
        assert results[0].score == 0.85

    @patch('requests.post')
    def test_search_no_api_key(self, mock_post):
        """Test search without API key."""
        with patch.dict('os.environ', {}, clear=True):
            client = TavilyClient(api_key=None)
            results = client.search("momentum")

            assert results == []
            mock_post.assert_not_called()

    @patch('requests.post')
    def test_search_api_error(self, mock_post):
        """Test search with API error."""
        import requests
        mock_post.side_effect = requests.exceptions.RequestException("API Error")

        client = TavilyClient(api_key="test-key")
        results = client.search("momentum")

        assert results == []

    @patch('requests.post')
    def test_search_research_papers(self, mock_post):
        """Test research paper specific search."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"results": []}
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response

        client = TavilyClient(api_key="test-key")
        client.search_research_papers("factor investing")

        # Check that academic domains are included
        call_args = mock_post.call_args
        payload = call_args[1]['json']
        assert "arxiv.org" in payload.get('include_domains', [])
        assert "ssrn.com" in payload.get('include_domains', [])


class TestSearchResult:
    """Tests for SearchResult dataclass."""

    def test_to_dict(self):
        """Test conversion to dict."""
        result = SearchResult(
            title="Test Paper",
            url="https://example.com/paper",
            content="Test content",
            score=0.75,
            published_date="2024-01-01"
        )

        d = result.to_dict()
        assert d['title'] == "Test Paper"
        assert d['score'] == 0.75
        assert d['published_date'] == "2024-01-01"


class TestDeepSearchTool:
    """Tests for DeepSearchTool."""

    @pytest.fixture
    def mock_config(self, tmp_path):
        """Create a mock config."""
        config = Mock()
        config.home_dir = tmp_path
        return config

    def test_tool_name(self, mock_config):
        """Test tool name property."""
        tool = DeepSearchTool(mock_config)
        assert tool.name == "deep_search"

    def test_tool_description(self, mock_config):
        """Test tool description property."""
        tool = DeepSearchTool(mock_config)
        assert "Tavily" in tool.description

    @patch.object(TavilyClient, 'is_configured', return_value=False)
    def test_execute_no_api_key(self, mock_configured, mock_config):
        """Test execution without API key."""
        tool = DeepSearchTool(mock_config)
        result = tool.execute("momentum")

        assert not result.success
        assert "TAVILY_API_KEY" in result.error

    @patch.object(TavilyClient, 'search_research_papers')
    @patch.object(TavilyClient, 'is_configured', return_value=True)
    def test_execute_no_results(self, mock_configured, mock_search, mock_config):
        """Test execution with no results."""
        mock_search.return_value = []

        tool = DeepSearchTool(mock_config)
        result = tool.execute("obscure query xyz")

        assert not result.success
        assert "No results" in result.error

    @patch.object(TavilyClient, 'search_research_papers')
    @patch.object(TavilyClient, 'is_configured', return_value=True)
    def test_execute_success(self, mock_configured, mock_search, mock_config):
        """Test successful execution."""
        mock_search.return_value = [
            SearchResult(
                title="Momentum Paper",
                url="https://arxiv.org/test",
                content="Trading strategy content",
                score=0.8,
            )
        ]

        tool = DeepSearchTool(mock_config)
        result = tool.execute("momentum", filter_relevance=False)

        assert result.success
        assert len(result.data) == 1
        assert result.data[0]['title'] == "Momentum Paper"

    @patch.object(TavilyClient, 'search_research_papers')
    @patch.object(TavilyClient, 'is_configured', return_value=True)
    def test_execute_filters_low_score(self, mock_configured, mock_search, mock_config):
        """Test that low-score results are filtered."""
        mock_search.return_value = [
            SearchResult(title="High Score", url="https://test1.com", content="Good", score=0.8),
            SearchResult(title="Low Score", url="https://test2.com", content="Bad", score=0.3),
        ]

        tool = DeepSearchTool(mock_config)
        result = tool.execute("test", filter_relevance=False, min_relevance_score=0.5)

        assert result.success
        assert len(result.data) == 1
        assert result.data[0]['title'] == "High Score"

    @patch.object(TavilyClient, 'search_research_papers')
    @patch.object(TavilyClient, 'is_configured', return_value=True)
    def test_execute_saves_cache(self, mock_configured, mock_search, mock_config):
        """Test that results are saved to articles.json."""
        mock_search.return_value = [
            SearchResult(title="Test", url="https://test.com", content="Content", score=0.9)
        ]

        tool = DeepSearchTool(mock_config)
        result = tool.execute("test", filter_relevance=False)

        assert result.success
        cache_file = mock_config.home_dir / "articles.json"
        assert cache_file.exists()

    @patch.object(TavilyClient, 'search_research_papers')
    @patch.object(TavilyClient, 'is_configured', return_value=True)
    def test_convert_to_articles_format(self, mock_configured, mock_search, mock_config):
        """Test conversion to standard article format."""
        mock_search.return_value = [
            SearchResult(
                title="ArXiv Paper",
                url="https://arxiv.org/abs/2401.12345",
                content="Abstract text",
                score=0.85,
                published_date="2024-01-15"
            )
        ]

        tool = DeepSearchTool(mock_config)
        result = tool.execute("test", filter_relevance=False)

        assert result.success
        article = result.data[0]
        assert article['title'] == "ArXiv Paper"
        assert article['URL'] == "https://arxiv.org/abs/2401.12345"
        assert article['abstract'] == "Abstract text"
        assert article['relevance_score'] == 0.85
        assert article['source'] == "tavily_deep_search"


class TestLLMFiltering:
    """Tests for LLM-based relevance filtering."""

    @pytest.fixture
    def mock_config(self, tmp_path):
        """Create a mock config."""
        config = Mock()
        config.home_dir = tmp_path
        return config

    @patch.object(DeepSearchTool, '_filter_for_implementable')
    @patch.object(TavilyClient, 'search_research_papers')
    @patch.object(TavilyClient, 'is_configured', return_value=True)
    def test_llm_filter_keeps_relevant(self, mock_configured, mock_search, mock_filter, mock_config):
        """Test LLM filter keeps relevant papers."""
        test_results = [
            SearchResult(title="Good Paper", url="https://test.com", content="Strategy", score=0.8)
        ]
        mock_search.return_value = test_results
        # Mock filter to return same results (all kept)
        mock_filter.return_value = test_results

        tool = DeepSearchTool(mock_config)
        result = tool.execute("test", filter_relevance=True)

        assert result.success
        assert len(result.data) == 1
        mock_filter.assert_called_once()

    @patch.object(DeepSearchTool, '_filter_for_implementable')
    @patch.object(TavilyClient, 'search_research_papers')
    @patch.object(TavilyClient, 'is_configured', return_value=True)
    def test_llm_filter_removes_irrelevant(self, mock_configured, mock_search, mock_filter, mock_config):
        """Test LLM filter removes irrelevant papers."""
        mock_search.return_value = [
            SearchResult(title="Bad Paper", url="https://test.com", content="Not a strategy", score=0.8)
        ]
        # Mock filter to return empty list (all filtered out)
        mock_filter.return_value = []

        tool = DeepSearchTool(mock_config)
        result = tool.execute("test", filter_relevance=True)

        # Should fail because all results filtered out
        assert not result.success
        assert "No implementable" in result.error

    @patch.object(TavilyClient, 'search_research_papers')
    @patch.object(TavilyClient, 'is_configured', return_value=True)
    def test_filter_skipped_when_disabled(self, mock_configured, mock_search, mock_config):
        """Test that filter is skipped when filter_relevance=False."""
        mock_search.return_value = [
            SearchResult(title="Paper", url="https://test.com", content="Content", score=0.8)
        ]

        tool = DeepSearchTool(mock_config)
        # With filter_relevance=False, should not call LLM
        result = tool.execute("test", filter_relevance=False)

        assert result.success
        assert len(result.data) == 1
