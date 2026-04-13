"""Anti-spider feature checker - UA, rate limit, captcha trigger detection"""
import logging
import time
from typing import Optional

from ..models.result import AntiSpiderResult
from ..utils.http_client import HttpClient
from .base_checker import BaseChecker
from ..utils.cache import cache_manager

logger = logging.getLogger(__name__)

CHALLENGE_KEYWORDS = [
    "checking your browser",
    "please wait",
    "just a moment",
    "cloudflare",
    "access denied",
    "ddos-guard",
    "security check",
]


class AntiSpiderChecker(BaseChecker):
    """Check anti-scraping mechanisms"""

    def __init__(self, client: HttpClient, deep: bool = False):
        self.client = client
        self.deep = deep
        self.max_requests = 50 if deep else 10

    async def check(self, url: str) -> AntiSpiderResult:
        """Run all anti-spider checks with caching"""
        logger.info(f"Starting anti-spider check for {url}")
        
        # Check cache first if not disabled
        if not getattr(self.client, 'disable_cache', False):
            # For anti_spider, we need to include the deep flag in the cache key
            cached_result = cache_manager.get(url, "anti_spider", self.deep)
            if cached_result is not None:
                logger.info(f"Using cached anti-spider check result for {url}")
                # Convert dict back to AntiSpiderResult object
                result = AntiSpiderResult(**cached_result)
                return result

        result = AntiSpiderResult()

        try:
            response = self.client.get(url)
            result.default_status_code = response.status_code
            result.default_response_length = len(response.text)

            if response.history:
                result.default_redirect = response.url
            else:
                result.default_redirect = ""

            ua_result = await self._test_user_agent(url)
            result.user_agent_check = ua_result

            referer_result = await self._test_referer(url)
            result.referer_check = referer_result

            cookie_result = await self._test_cookie_dependency(url)
            result.cookie_dependency = cookie_result

            rate_limit_result = await self._test_rate_limit(url)
            result.rate_limit_triggered = rate_limit_result["triggered"]
            result.rate_limit_threshold = rate_limit_result.get("threshold", "")

            captcha_result = await self._test_captcha_trigger(url)
            result.captcha_trigger = captcha_result

            js_challenge = await self._test_js_challenge(url)
            result.js_challenge = js_challenge

        except Exception as e:
            logger.error(f"Anti-spider check failed: {e}")

        logger.info(f"Anti-spider check completed for {url}")
        
        # Cache the result
        if not getattr(self.client, 'disable_cache', False):
            cache_manager.set(url, "anti_spider", result.to_dict(), self.deep)

        return result

    async def _test_user_agent(self, url: str) -> str:
        """Test if User-Agent is required"""
        try:
            response = self.client.get_without_ua(url)

            if response.status_code in [403, 406]:
                logger.info("User-Agent check: FAILED (blocked without UA)")
                return "fail"

            if response.status_code == 200:
                return "pass"

        except Exception as e:
            logger.debug(f"UA test failed: {e}")

        return "unknown"

    async def _test_referer(self, url: str) -> str:
        """Test if Referer is required"""
        try:
            response = self.client.get_without_referer(url)

            if response.status_code in [403, 406]:
                logger.info("Referer check: FAILED (blocked without Referer)")
                return "fail"

            if response.status_code == 200:
                return "pass"

        except Exception as e:
            logger.debug(f"Referer test failed: {e}")

        return "unknown"

    async def _test_cookie_dependency(self, url: str) -> str:
        """Test if site depends on cookies for session"""
        try:
            response1 = self.client.get(url)

            cookies = self.client._session.cookies.get_dict() if hasattr(self.client, '_session') else {}

            if not cookies:
                return "no"

            for cookie_name in cookies:
                self.client._session.cookies.set(cookie_name, "")

            response2 = self.client.get(url)

            if response2.status_code != response1.status_code:
                return "yes"

            if "login" in response2.url.lower() or "signin" in response2.url.lower():
                return "yes"

        except Exception as e:
            logger.debug(f"Cookie test failed: {e}")

        return "unknown"

    async def _test_rate_limit(self, url: str) -> dict:
        """Test if site has rate limiting"""
        if self.deep:
            intervals = [1.0, 0.8, 0.6, 0.4, 0.2, 0.2, 0.2, 0.2, 0.2, 0.2]
            test_count = 10
        else:
            intervals = [1.0, 0.5, 0.3, 0.2, 0.2]
            test_count = 5

        results = []
        triggered = False
        threshold_info = ""

        try:
            for i in range(test_count):
                response = self.client.get(url)
                results.append(response.status_code)

                if response.status_code in [429, 503]:
                    triggered = True
                    threshold_info = f"约 {i+1} 次请求后触发"
                    logger.info(f"Rate limit triggered after {i+1} requests")
                    break

                if i < len(intervals) - 1:
                    time.sleep(intervals[i])

        except Exception as e:
            logger.debug(f"Rate limit test failed: {e}")

        if not triggered:
            for status in results:
                if status != 200:
                    triggered = True
                    threshold_info = "存在异常响应"
                    break

        return {"triggered": triggered, "threshold": threshold_info}

    async def _test_captcha_trigger(self, url: str) -> bool:
        """Test if accessing the site triggers captcha"""
        try:
            for _ in range(3):
                response = self.client.get(url)

                text = response.text.lower()

                captcha_keywords = [
                    "captcha",
                    "recaptcha",
                    "hcaptcha",
                    "turnstile",
                    "verify you're human",
                    "请验证",
                    "验证",
                ]

                for keyword in captcha_keywords:
                    if keyword in text:
                        logger.info(f"Captcha triggered: found '{keyword}'")
                        return True

                time.sleep(1)

        except Exception as e:
            logger.debug(f"Captcha trigger test failed: {e}")

        return False

    async def _test_js_challenge(self, url: str) -> bool:
        """Test if site has JavaScript challenge (like Cloudflare)"""
        try:
            response = self.client.get(url)

            text = response.text.lower()

            for keyword in CHALLENGE_KEYWORDS:
                if keyword in text:
                    logger.info(f"JS challenge detected: found '{keyword}'")
                    return True

            if response.status_code in [403, 503]:
                if "cloudflare" in text or "cf-ray" in str(response.headers).lower():
                    return True

        except Exception as e:
            logger.debug(f"JS challenge test failed: {e}")

        return False
