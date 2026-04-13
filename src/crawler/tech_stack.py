"""Technology stack checker - framework, WAF, CDN detection"""
import logging

from bs4 import BeautifulSoup

from ..models.result import TechStackResult
from ..utils.http_client import HttpClient
from ..utils.fingerprint import (
    detect_waf,
    detect_framework,
    detect_captcha,
    detect_fingerprinting,
)
from .base_checker import BaseChecker
from ..utils.cache import cache_manager

logger = logging.getLogger(__name__)


class TechStackChecker(BaseChecker[TechStackResult]):
    """Check technology stack used by the website"""

    def __init__(self, client: HttpClient):
        self.client = client

    async def check(self, url: str) -> TechStackResult:
        """Run all technology stack checks with caching"""
        logger.info(f"Starting tech stack check for {url}")
        
        # Check cache first if not disabled
        if not getattr(self.client, 'disable_cache', False):
            cached_result = cache_manager.get(url, "tech_stack", False)
            if cached_result is not None:
                logger.info(f"Using cached tech stack check result for {url}")
                # Convert dict back to TechStackResult object
                result = TechStackResult(**cached_result)
                return result

        result = TechStackResult()

        try:
            response = self.client.get(url)
            if response.status_code != 200:
                logger.warning(f"Failed to fetch {url}: status {response.status_code}")
                return result

            headers = dict(response.headers)
            body = response.text

            result.framework = self._detect_framework(body)

            result.cdn_waf = self._detect_waf(headers, body)

            captcha = self._detect_captcha(body)
            result.captcha = captcha

            result.fingerprinting = self._detect_fingerprinting(body)

            result.dynamic_rendering = self._detect_dynamic_rendering(
                url, response.text
            )

            result.content_loading = self._detect_content_loading(body)

        except Exception as e:
            logger.error(f"Tech stack check failed: {e}")

        logger.info(f"Tech stack check completed for {url}")
        
        # Cache the result
        if not getattr(self.client, 'disable_cache', False):
            cache_manager.set(url, "tech_stack", result.to_dict(), False)

        return result

    def _detect_framework(self, body: str) -> str:
        """Detect frontend framework"""
        frameworks = detect_framework(body)

        if not frameworks:
            return "static"

        if len(frameworks) == 1:
            return frameworks[0]

        return frameworks[0]

    def _detect_waf(self, headers: dict, body: str) -> str:
        """Detect WAF/CDN"""
        wafs = detect_waf(headers, body)

        if not wafs:
            return "none"

        return wafs[0]

    def _detect_captcha(self, body: str) -> list:
        """Detect captcha providers"""
        return detect_captcha(body)

    def _detect_fingerprinting(self, body: str) -> bool:
        """Detect browser fingerprinting"""
        return detect_fingerprinting(body)

    def _detect_dynamic_rendering(self, url: str, static_body: str) -> bool:
        """Detect if content is rendered dynamically via JavaScript"""
        soup = BeautifulSoup(static_body, "lxml")

        body_content = soup.find("body")
        if not body_content:
            return True

        text_length = len(body_content.get_text(strip=True))

        if text_length < 100:
            return True

        has_loading_indicators = [
            "loading",
            "spinner",
            "skeleton",
            "placeholder",
        ]

        body_str = str(body_content).lower()
        for indicator in has_loading_indicators:
            if indicator in body_str:
                logger.debug(f"Found loading indicator: {indicator}")
                return True

        has_react_vue_attrs = [
            "data-reactroot",
            "data-v-",
            "ng-app",
            "id=\"app\"",
            "id=\"root\"",
        ]

        for attr in has_react_vue_attrs:
            if attr in static_body:
                return True

        return False

    def _detect_content_loading(self, body: str) -> str:
        """Detect how content is loaded"""
        soup = BeautifulSoup(body, "lxml")

        has_api_calls = [
            "fetch(",
            "axios.",
            "$.ajax",
            "XMLHttpRequest",
            "async",
            "await fetch",
        ]

        body_str = body.lower()
        api_call_count = sum(1 for pattern in has_api_calls if pattern in body_str)

        if api_call_count >= 2:
            return "client-side"

        json_ld = soup.find_all("script", type="application/ld+json")
        if json_ld:
            return "ssr"

        if self._has_dynamic_content_hints(body):
            return "client-side"

        return "server-side"

    def _has_dynamic_content_hints(self, body: str) -> bool:
        """Check for hints that content is loaded dynamically"""
        dynamic_hints = [
            "v-if",
            "v-show",
            "v-for",
            "ng-if",
            "ng-show",
            "react",
            "useeffect",
            "useState",
        ]

        body_lower = body.lower()
        return any(hint in body_lower for hint in dynamic_hints)
