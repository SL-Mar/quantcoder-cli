"""HTTP utilities with retry logic and caching support."""

import hashlib
import json
import logging
import time
from pathlib import Path
from typing import Any, Dict, Optional
from functools import wraps

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)


# Default configuration
DEFAULT_TIMEOUT = 30  # seconds
DEFAULT_RETRIES = 3
DEFAULT_BACKOFF_FACTOR = 0.5  # exponential backoff: 0.5, 1, 2 seconds
DEFAULT_CACHE_TTL = 3600  # 1 hour in seconds


def create_session_with_retries(
    retries: int = DEFAULT_RETRIES,
    backoff_factor: float = DEFAULT_BACKOFF_FACTOR,
    status_forcelist: tuple = (429, 500, 502, 503, 504),
) -> requests.Session:
    """
    Create a requests Session with automatic retry support.

    Args:
        retries: Number of retries for failed requests
        backoff_factor: Factor for exponential backoff between retries
        status_forcelist: HTTP status codes that trigger a retry

    Returns:
        Configured requests.Session object
    """
    session = requests.Session()

    retry_strategy = Retry(
        total=retries,
        backoff_factor=backoff_factor,
        status_forcelist=status_forcelist,
        allowed_methods=["HEAD", "GET", "POST", "PUT", "DELETE", "OPTIONS", "TRACE"],
        raise_on_status=False,
    )

    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)

    return session


def make_request_with_retry(
    url: str,
    method: str = "GET",
    headers: Optional[Dict[str, str]] = None,
    params: Optional[Dict[str, Any]] = None,
    data: Optional[Dict[str, Any]] = None,
    json_data: Optional[Dict[str, Any]] = None,
    timeout: int = DEFAULT_TIMEOUT,
    retries: int = DEFAULT_RETRIES,
    backoff_factor: float = DEFAULT_BACKOFF_FACTOR,
) -> requests.Response:
    """
    Make an HTTP request with automatic retry on failure.

    Args:
        url: The URL to request
        method: HTTP method (GET, POST, etc.)
        headers: Optional headers dict
        params: Optional query parameters
        data: Optional form data
        json_data: Optional JSON body
        timeout: Request timeout in seconds
        retries: Number of retry attempts
        backoff_factor: Exponential backoff factor

    Returns:
        requests.Response object

    Raises:
        requests.exceptions.RequestException: If all retries fail
    """
    session = create_session_with_retries(retries, backoff_factor)

    default_headers = {
        "User-Agent": "QuantCoder/2.0 (https://github.com/SL-Mar/quantcoder)"
    }
    if headers:
        default_headers.update(headers)

    try:
        response = session.request(
            method=method,
            url=url,
            headers=default_headers,
            params=params,
            data=data,
            json=json_data,
            timeout=timeout,
        )
        return response
    finally:
        session.close()


class ResponseCache:
    """Simple file-based cache for HTTP responses."""

    def __init__(self, cache_dir: Optional[Path] = None, ttl: int = DEFAULT_CACHE_TTL):
        """
        Initialize the response cache.

        Args:
            cache_dir: Directory to store cache files
            ttl: Time-to-live for cache entries in seconds
        """
        self.cache_dir = cache_dir or Path.home() / ".quantcoder" / "cache"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.ttl = ttl

    def _get_cache_key(self, url: str, params: Optional[Dict] = None) -> str:
        """Generate a cache key from URL and params."""
        cache_input = url
        if params:
            cache_input += json.dumps(params, sort_keys=True)
        return hashlib.sha256(cache_input.encode()).hexdigest()

    def _get_cache_path(self, cache_key: str) -> Path:
        """Get the file path for a cache key."""
        return self.cache_dir / f"{cache_key}.json"

    def get(self, url: str, params: Optional[Dict] = None) -> Optional[Dict[str, Any]]:
        """
        Get a cached response if it exists and is not expired.

        Args:
            url: The request URL
            params: Optional query parameters

        Returns:
            Cached data dict or None if not found/expired
        """
        cache_key = self._get_cache_key(url, params)
        cache_path = self._get_cache_path(cache_key)

        if not cache_path.exists():
            return None

        try:
            with open(cache_path, "r") as f:
                cached = json.load(f)

            # Check if expired
            if time.time() - cached.get("timestamp", 0) > self.ttl:
                logger.debug(f"Cache expired for {url}")
                cache_path.unlink(missing_ok=True)
                return None

            logger.debug(f"Cache hit for {url}")
            return cached.get("data")

        except (json.JSONDecodeError, KeyError) as e:
            logger.warning(f"Invalid cache entry: {e}")
            cache_path.unlink(missing_ok=True)
            return None

    def set(self, url: str, data: Any, params: Optional[Dict] = None) -> None:
        """
        Store a response in the cache.

        Args:
            url: The request URL
            data: Data to cache (must be JSON serializable)
            params: Optional query parameters
        """
        cache_key = self._get_cache_key(url, params)
        cache_path = self._get_cache_path(cache_key)

        try:
            with open(cache_path, "w") as f:
                json.dump(
                    {
                        "timestamp": time.time(),
                        "url": url,
                        "data": data,
                    },
                    f,
                )
            logger.debug(f"Cached response for {url}")
        except (TypeError, OSError) as e:
            logger.warning(f"Failed to cache response: {e}")

    def clear(self) -> int:
        """
        Clear all cached responses.

        Returns:
            Number of cache entries cleared
        """
        count = 0
        for cache_file in self.cache_dir.glob("*.json"):
            try:
                cache_file.unlink()
                count += 1
            except OSError:
                pass
        logger.info(f"Cleared {count} cache entries")
        return count

    def clear_expired(self) -> int:
        """
        Clear only expired cache entries.

        Returns:
            Number of expired entries cleared
        """
        count = 0
        for cache_file in self.cache_dir.glob("*.json"):
            try:
                with open(cache_file, "r") as f:
                    cached = json.load(f)
                if time.time() - cached.get("timestamp", 0) > self.ttl:
                    cache_file.unlink()
                    count += 1
            except (json.JSONDecodeError, OSError):
                cache_file.unlink(missing_ok=True)
                count += 1
        logger.debug(f"Cleared {count} expired cache entries")
        return count


# Global cache instance
_response_cache: Optional[ResponseCache] = None


def get_response_cache(cache_dir: Optional[Path] = None) -> ResponseCache:
    """Get or create the global response cache instance."""
    global _response_cache
    if _response_cache is None:
        _response_cache = ResponseCache(cache_dir)
    return _response_cache


def cached_request(
    url: str,
    params: Optional[Dict] = None,
    headers: Optional[Dict] = None,
    timeout: int = DEFAULT_TIMEOUT,
    use_cache: bool = True,
    cache_ttl: int = DEFAULT_CACHE_TTL,
) -> Optional[Dict[str, Any]]:
    """
    Make a GET request with caching and retry support.

    Args:
        url: The URL to request
        params: Optional query parameters
        headers: Optional headers
        timeout: Request timeout
        use_cache: Whether to use caching
        cache_ttl: Cache time-to-live in seconds

    Returns:
        JSON response data or None on failure
    """
    cache = get_response_cache()

    # Check cache first
    if use_cache:
        cached_data = cache.get(url, params)
        if cached_data is not None:
            return cached_data

    # Make request with retries
    try:
        response = make_request_with_retry(
            url=url,
            method="GET",
            headers=headers,
            params=params,
            timeout=timeout,
        )
        response.raise_for_status()
        data = response.json()

        # Cache the response
        if use_cache:
            cache.set(url, data, params)

        return data

    except requests.exceptions.RequestException as e:
        logger.error(f"Request failed: {e}")
        return None
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON response: {e}")
        return None
