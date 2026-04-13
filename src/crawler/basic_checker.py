"""Basic information checker - robots.txt, sitemap, RSS, API docs"""
import logging
import re
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

from ..models.result import BasicResult
from ..utils.http_client import HttpClient
from .base_checker import BaseChecker
from ..utils.cache import cache_manager

logger = logging.getLogger(__name__)

ROBOTS_TXT_PATHS = ["/robots.txt"]
SITEMAP_PATHS = [
    "/sitemap.xml",
    "/sitemap_index.xml",
    "/sitemap1.xml",
    "/sitemap2.xml",
]
RSS_PATHS = ["/feed", "/rss", "/feed.xml", "/rss.xml", "/atom.xml", "/atom"]
API_DOC_PATTERNS = ["/api", "/swagger", "/docs", "/documentation", "/api-docs"]
LEGAL_PATTERNS = [
    r"禁止.*爬取",
    r"禁止.*采集",
    r"禁止.*抓取",
    r"robots?.*denied",
    r"no\s*robots?",
    r"copyright.*all\s*rights?\s*reserved",
]


class BasicChecker(BaseChecker[BasicResult]):
    """Check basic information about a website"""

    def __init__(self, client: HttpClient):
        self.client = client

    async def check(self, url: str) -> BasicResult:
        """Run all basic checks with caching"""
        logger.info(f"Starting basic check for {url}")
        
        # Check cache first if not disabled
        if not getattr(self.client, 'disable_cache', False):
            cached_result = cache_manager.get(url, "basic", False)
            if cached_result is not None:
                logger.info(f"Using cached basic check result for {url}")
                # Convert dict back to BasicResult object
                result = BasicResult(**cached_result)
                return result

        domain = self.client.get_domain(url)

        result = BasicResult()

        robots_exists, robots_content = await self._check_robots_txt(domain)
        result.robots_txt_exists = robots_exists
        result.robots_txt_content = robots_content
        result.robots_txt_full_disallow = self._is_full_disallow(robots_content)

        result.sitemap_urls = await self._check_sitemap(domain, robots_content)
        result.html_sitemap = await self._check_html_sitemap(url)

        result.rss_urls = await self._check_rss(domain)

        api_docs = await self._check_api_docs(url)
        result.api_docs = api_docs

        result.legal_notice = await self._check_legal_notice(url)

        logger.info(f"Basic check completed for {url}")
        
        # Cache the result
        if not getattr(self.client, 'disable_cache', False):
            cache_manager.set(url, "basic", result.to_dict(), False)

        return result

    async def _check_robots_txt(self, domain: str) -> tuple[bool, str]:
        """Check robots.txt existence and content"""
        for path in ROBOTS_TXT_PATHS:
            url = urljoin(domain, path)
            try:
                response = self.client.get(url)
                if response.status_code == 200:
                    logger.info(f"Found robots.txt: {url}")
                    return True, response.text
            except Exception as e:
                logger.debug(f"Failed to fetch {url}: {e}")

        logger.info(f"No robots.txt found for {domain}")
        return False, ""

    def _is_full_disallow(self, content: str) -> bool:
        """Check if robots.txt fully disallows all access"""
        if not content:
            return False

        lines = content.lower().split("\n")
        in_user_agent_block = False
        disallow_all = False

        for line in lines:
            line = line.strip()

            if line.startswith("user-agent:"):
                in_user_agent_block = True
                continue

            if line.startswith("disallow:"):
                if in_user_agent_block and line.split(":", 1)[1].strip() == "/":
                    disallow_all = True
                continue

            if line.startswith("user-agent:") or line.startswith("sitemap:"):
                in_user_agent_block = False

        return disallow_all

    async def _check_sitemap(self, domain: str, robots_content: str) -> list[str]:
        """Check sitemap.xml existence"""
        sitemap_urls = []

        for path in SITEMAP_PATHS:
            url = urljoin(domain, path)
            try:
                response = self.client.get(url)
                if response.status_code == 200:
                    sitemap_urls.append(url)
                    logger.info(f"Found sitemap: {url}")
            except Exception:
                pass

        if not sitemap_urls and robots_content:
            for line in robots_content.split("\n"):
                if line.lower().startswith("sitemap:"):
                    sitemap_url = line.split(":", 1)[1].strip()
                    if sitemap_url:
                        sitemap_urls.append(sitemap_url)
                        logger.info(f"Found sitemap in robots.txt: {sitemap_url}")

        return sitemap_urls

    async def _check_html_sitemap(self, url: str) -> bool:
        """Check for HTML sitemap link in page"""
        try:
            response = self.client.get(url)
            if response.status_code != 200:
                return False

            soup = BeautifulSoup(response.text, "lxml")

            links = soup.find_all("link", rel="sitemap")
            # BeautifulSoup's find_all returns an empty list when no matches found
            if links:
                logger.info(f"Found HTML sitemap link")
                return True

            sitemap_link = soup.find("a", string=lambda text: text and re.search(r"sitemap", text, re.I))
            if sitemap_link:
                return True

        except Exception as e:
            logger.debug(f"Failed to check HTML sitemap: {e}")

        return False

    async def _check_rss(self, domain: str) -> list[str]:
        """Check for RSS/Atom feeds"""
        rss_urls = []

        for path in RSS_PATHS:
            url = urljoin(domain, path)
            try:
                response = self.client.get(url)
                if response.status_code == 200:
                    content_type = response.headers.get("content-type", "").lower()
                    if "xml" in content_type or "rss" in content_type or "atom" in content_type:
                        rss_urls.append(url)
                        logger.info(f"Found RSS/Atom: {url}")
            except Exception:
                pass

        return rss_urls

    async def _check_api_docs(self, url: str) -> list[str]:
        """Check for API documentation links"""
        api_docs = []

        try:
            response = self.client.get(url)
            if response.status_code != 200:
                return []

            soup = BeautifulSoup(response.text, "lxml")

            for pattern in API_DOC_PATTERNS:
                links = soup.find_all("a", href=re.compile(pattern, re.I))
                for link in links:
                     href = link.get("href")
                     if href and isinstance(href, str):
                         if not href.startswith("http"):
                             href = urljoin(url, href)
                         if href not in api_docs:
                             api_docs.append(href)

            api_links = soup.find_all("a", href=re.compile(r"/api[/$]"))
            for link in api_links:
                href = link.get("href")
                if href:
                    if not href.startswith("http"):
                        href = urljoin(url, href)
                    if href not in api_docs:
                        api_docs.append(href)

        except Exception as e:
            logger.debug(f"Failed to check API docs: {e}")

        if api_docs:
            logger.info(f"Found API docs: {api_docs}")

        return api_docs

    async def _check_legal_notice(self, url: str) -> bool:
        """Check for legal notices that prohibit crawling"""
        try:
            response = self.client.get(url)
            if response.status_code != 200:
                return False

            text = response.text.lower()

            for pattern in LEGAL_PATTERNS:
                if re.search(pattern, text):
                    logger.info(f"Found legal notice prohibiting crawling")
                    return True

        except Exception as e:
            logger.debug(f"Failed to check legal notice: {e}")

        return False
