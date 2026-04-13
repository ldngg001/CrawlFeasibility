"""Assessment module - generate comprehensive evaluation"""
import logging

from ..models.result import (
    AssessmentResult,
    BasicResult,
    TechStackResult,
    AntiSpiderResult,
)

logger = logging.getLogger(__name__)


class Assessor:
    """Generate comprehensive assessment based on check results"""

    def __init__(self):
        pass

    def assess(
        self, basic: BasicResult, tech: TechStackResult, anti: AntiSpiderResult
    ) -> AssessmentResult:
        """Generate assessment from all check results"""
        logger.info("Generating assessment")

        result = AssessmentResult()

        result.difficulty = self._calculate_difficulty(basic, tech, anti)

        result.recommended_tool = self._recommend_tool(basic, tech, anti)

        result.key_risks = self._identify_risks(basic, tech, anti)

        result.code_template = self._generate_code_template(result.recommended_tool)

        result.legal_note = self._generate_legal_note(basic)

        logger.info(f"Assessment completed: difficulty = {result.difficulty}")
        return result

    def _calculate_difficulty(
        self, basic: BasicResult, tech: TechStackResult, anti: AntiSpiderResult
    ) -> str:
        """Calculate overall difficulty"""
        score = 0

        if basic.robots_txt_exists and basic.robots_txt_full_disallow:
            score += 3
        elif basic.robots_txt_exists:
            score += 1

        if basic.legal_notice:
            score += 2

        if tech.cdn_waf != "none":
            score += 2

        if tech.captcha:
            score += 2

        if tech.dynamic_rendering:
            score += 2

        if anti.user_agent_check == "fail":
            score += 1

        if anti.cookie_dependency == "yes":
            score += 1

        if anti.rate_limit_triggered:
            score += 2

        if anti.captcha_trigger:
            score += 2

        if anti.js_challenge:
            score += 3

        if score >= 8:
            return "high"
        elif score >= 4:
            return "medium"
        else:
            return "low"

    def _recommend_tool(
        self, basic: BasicResult, tech: TechStackResult, anti: AntiSpiderResult
    ) -> str:
        """Recommend scraping tool based on results"""
        if anti.js_challenge or tech.cdn_waf == "cloudflare":
            return "Playwright + stealth plugin"

        if tech.dynamic_rendering:
            if tech.captcha:
                return "Playwright + 验证码对接"
            return "Playwright 或 Selenium"

        if tech.cdn_waf != "none":
            return "Selenium + 代理池"

        if anti.captcha_trigger or tech.captcha:
            return "requests + 验证码平台"

        if anti.rate_limit_triggered:
            return "requests + 代理池 + 限速"

        if tech.framework in ["react", "vue", "angular"]:
            return "Playwright 或 requests + API分析"

        return "requests + BeautifulSoup"

    def _identify_risks(
        self, basic: BasicResult, tech: TechStackResult, anti: AntiSpiderResult
    ) -> list[str]:
        """Identify key risks"""
        risks = []

        if basic.robots_txt_exists and basic.robots_txt_full_disallow:
            risks.append("robots.txt 全面禁止访问")

        if basic.legal_notice:
            risks.append("网站明确禁止爬取，可能存在法律风险")

        if tech.cdn_waf == "cloudflare":
            risks.append("Cloudflare 防护，可能需要处理 JS 挑战")

        if tech.cdn_waf == "aliyun":
            risks.append("阿里云 WAF 防护")

        if tech.captcha or anti.captcha_trigger:
            risks.append("存在验证码，需要对接打码平台")

        if anti.js_challenge:
            risks.append("存在 JS 挑战，需要浏览器环境")

        if anti.rate_limit_triggered:
            risks.append(f"存在频率限制 ({anti.rate_limit_threshold})")

        if anti.cookie_dependency == "yes":
            risks.append("依赖 Cookie 维持会话")

        if tech.dynamic_rendering:
            risks.append("内容动态渲染，需要 JS 执行")

        if tech.fingerprinting:
            risks.append("网站检测浏览器指纹")

        return risks

    def _generate_code_template(self, recommended_tool: str) -> str:
        """Generate code template based on recommended tool"""
        if "Playwright" in recommended_tool:
            return '''import asyncio
from playwright.async_api import async_playwright

async def crawl():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        await page.goto("https://example.com")
        content = await page.content()
        await browser.close()
        return content

asyncio.run(crawl())'''

        if "Selenium" in recommended_tool:
            return '''from selenium import webdriver
from selenium.webdriver.chrome.options import Options

options = Options()
options.add_argument("--headless")

driver = webdriver.Chrome(options=options)
driver.get("https://example.com")
content = driver.page_source
driver.quit()'''

        return '''import requests
from bs4 import BeautifulSoup

response = requests.get("https://example.com")
soup = BeautifulSoup(response.text, "lxml")
# 提取内容...
print(soup.prettify())'''

    def _generate_legal_note(self, basic: BasicResult) -> str:
        """Generate legal compliance note"""
        notes = []

        if basic.legal_notice:
            notes.append("⚠️ 网站包含法律声明，建议仔细阅读并遵守")

        if basic.robots_txt_exists:
            notes.append("✓ 请遵守 robots.txt 规则")
        else:
            notes.append("⚠️ 未找到 robots.txt，请谨慎操作")

        notes.append("✓ 请注明数据来源，仅用于合法用途")
        notes.append("✓ 控制请求频率，避免对网站造成负担")

        return "\n".join(notes)
