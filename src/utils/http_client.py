"""HTTP client wrapper with error handling and logging"""
import logging
import time
from typing import Optional, Dict, Any
from urllib.parse import urljoin, urlparse

import requests as requests_lib
from requests.exceptions import RequestException, Timeout as RequestsTimeout

logger = logging.getLogger(__name__)

DEFAULT_USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
]


class HttpClientError(Exception):
    """Base exception for HTTP client errors"""
    pass


class NetworkError(HttpClientError):
    """Network related errors"""
    pass


class TimeoutError(HttpClientError):
    """Request timeout"""
    pass


class SSLError_(HttpClientError):
    """SSL certificate error"""
    pass


class ResponseWrapper:
    """Compatibility wrapper for response objects"""
    def __init__(self, response):
        self._response = response
    
    @property
    def status_code(self):
        return self._response.status_code
    
    @property
    def text(self):
        return self._response.text
    
    @property
    def content(self):
        return self._response.content
    
    @property
    def headers(self):
        return dict(self._response.headers)
    
    @property
    def url(self):
        return self._response.url
    
    @property
    def history(self):
        return getattr(self._response, 'history', [])


class HttpClient:
    """HTTP client with retry and error handling"""

    def __init__(
        self,
        timeout: int = 10,
        proxy: Optional[str] = None,
        user_agent: Optional[str] = None,
        max_retries: int = 2,
        verify_ssl: bool = False,
        disable_cache: bool = False,
    ):
        self.timeout = timeout
        self.proxy = proxy
        self.user_agent = user_agent or DEFAULT_USER_AGENTS[0]
        self.max_retries = max_retries
        self.verify_ssl = verify_ssl
        self.disable_cache = disable_cache
        self._headers = {"User-Agent": self.user_agent}
        self._session = requests_lib.Session()
        self._session.headers.update(self._headers)
        self._session.verify = verify_ssl
        if proxy:
            self._session.proxies = {"http": proxy, "https": proxy}

    def get(
        self,
        url: str,
        allow_redirects: bool = True,
        headers: Optional[Dict[str, str]] = None,
        timeout: Optional[int] = None,
    ) -> ResponseWrapper:
        """Send GET request with error handling"""
        request_headers = dict(self._headers)
        if headers:
            request_headers.update(headers)

        timeout_val = timeout or self.timeout

        for attempt in range(self.max_retries):
            try:
                logger.debug(f"GET {url} (attempt {attempt + 1})")
                response = self._session.get(
                    url,
                    allow_redirects=allow_redirects,
                    headers=request_headers,
                    timeout=timeout_val,
                )
                logger.debug(f"Response: {response.status_code} ({len(response.content)} bytes)")
                return ResponseWrapper(response)

            except RequestsTimeout:
                logger.warning(f"Timeout for {url}")
                if attempt == self.max_retries - 1:
                    raise TimeoutError(f"Request timeout: {url}")

            except requests_lib.exceptions.SSLError as e:
                logger.warning(f"SSL error for {url}: {e}")
                raise SSLError_(f"SSL error: {url}")

            except requests_lib.exceptions.ConnectionError as e:
                logger.warning(f"Connection error for {url}: {e}")
                if attempt == self.max_retries - 1:
                    raise NetworkError(f"Connection failed: {url}")

            except RequestException as e:
                logger.warning(f"Request error for {url}: {e}")
                if attempt == self.max_retries - 1:
                    raise NetworkError(f"Request failed: {url}")

            if attempt < self.max_retries - 1:
                time.sleep(0.5)

        raise NetworkError(f"Max retries exceeded: {url}")

    def get_with_custom_ua(
        self,
        url: str,
        user_agent: Optional[str] = None,
        allow_redirects: bool = True,
    ) -> ResponseWrapper:
        """Send request with custom User-Agent"""
        headers = {}
        if user_agent is not None:
            headers["User-Agent"] = user_agent
        return self.get(url, headers=headers, allow_redirects=allow_redirects)

    def get_without_ua(self, url: str) -> ResponseWrapper:
        """Send request without User-Agent"""
        headers = {"User-Agent": ""}
        return self.get(url, headers=headers)

    def get_without_referer(self, url: str, referer: str = "") -> ResponseWrapper:
        """Send request without Referer header"""
        headers = {"Referer": referer} if referer else {}
        return self.get(url, headers=headers)

    def fetch_robots_txt(self, domain: str) -> tuple[bool, str]:
        """Fetch robots.txt from domain"""
        if not domain.startswith(("http://", "https://")):
            domain = f"https://{domain}"

        robots_url = urljoin(domain, "/robots.txt")
        try:
            response = self.get(robots_url)
            if response.status_code == 200:
                logger.info(f"robots.txt found: {robots_url}")
                return True, response.text
            else:
                logger.info(f"robots.txt not found: {robots_url}")
                return False, ""
        except HttpClientError as e:
            logger.warning(f"Failed to fetch robots.txt: {e}")
            return False, ""

    def fetch_sitemap(self, domain: str) -> list[str]:
        """Try common sitemap locations"""
        if not domain.startswith(("http://", "https://")):
            domain = f"https://{domain}"

        sitemap_urls = [
            "/sitemap.xml",
            "/sitemap_index.xml",
            "/sitemap1.xml",
            "/sitemap_index.xml",
        ]

        found = []
        for path in sitemap_urls:
            url = urljoin(domain, path)
            try:
                response = self.get(url)
                if response.status_code == 200:
                    found.append(url)
                    logger.info(f"Found sitemap: {url}")
            except HttpClientError:
                pass

        return found

    def get_domain(self, url: str) -> str:
        """Extract domain from URL"""
        parsed = urlparse(url)
        return f"{parsed.scheme}://{parsed.netloc}"

    def close(self):
        """Close the HTTP client"""
        if hasattr(self, '_session'):
            self._session.close()