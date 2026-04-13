"""Result data models for CrawlFeasibility"""
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Optional, List, Dict, Any


@dataclass
class BasicResult:
    """基础信息检测结果"""
    robots_txt_exists: bool = False
    robots_txt_content: str = ""
    robots_txt_full_disallow: bool = False
    sitemap_urls: list = field(default_factory=list)
    html_sitemap: bool = False
    rss_urls: list = field(default_factory=list)
    api_docs: list = field(default_factory=list)
    legal_notice: bool = False

    def to_dict(self):
        return asdict(self)


@dataclass
class TechStackResult:
    """技术栈识别结果"""
    framework: str = "unknown"
    dynamic_rendering: bool = False
    content_loading: str = "unknown"
    cdn_waf: str = "none"
    captcha: list = field(default_factory=list)
    fingerprinting: bool = False

    def to_dict(self):
        return asdict(self)


@dataclass
class AntiSpiderResult:
    """反爬特征检测结果"""
    default_status_code: int = 0
    default_response_length: int = 0
    default_redirect: str = ""
    user_agent_check: str = "unknown"
    referer_check: str = "unknown"
    cookie_dependency: str = "unknown"
    rate_limit_triggered: bool = False
    rate_limit_threshold: str = ""
    captcha_trigger: bool = False
    js_challenge: bool = False

    def to_dict(self):
        return asdict(self)


@dataclass
class AssessmentResult:
    """综合评估结果"""
    difficulty: str = "unknown"
    recommended_tool: str = ""
    key_risks: list = field(default_factory=list)
    code_template: str = ""
    legal_note: str = ""

    def to_dict(self):
        return asdict(self)


@dataclass
class DataStructResult:
    """数据结构检测结果"""
    schema_org: List[Dict[str, Any]] = field(default_factory=list)
    opengraph: List[Dict[str, Any]] = field(default_factory=list)
    twitter: List[Dict[str, Any]] = field(default_factory=list)
    custom_patterns: Dict[str, List[str]] = field(default_factory=dict)

    def to_dict(self):
        return asdict(self)


@dataclass
class CrawlFeasibilityResult:
    """完整检测结果"""
    url: str
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    basic: Optional[BasicResult] = None
    tech_stack: Optional[TechStackResult] = None
    anti_spider: Optional[AntiSpiderResult] = None
    assessment: Optional[AssessmentResult] = None
    data_struct: Optional[DataStructResult] = None

    def to_dict(self):
        return {
            "url": self.url,
            "timestamp": self.timestamp,
            "basic": self.basic.to_dict() if self.basic else {},
            "tech_stack": self.tech_stack.to_dict() if self.tech_stack else {},
            "anti_spider": self.anti_spider.to_dict() if self.anti_spider else {},
            "data_struct": self.data_struct.to_dict() if self.data_struct else {},
            "assessment": self.assessment.to_dict() if self.assessment else {},
        }

    def to_json(self):
        import json
        return json.dumps(self.to_dict(), indent=2, ensure_ascii=False)

    def to_pretty_string(self) -> str:
        lines = [
            f"URL: {self.url}",
            f"时间: {self.timestamp}",
            "",
            "=== 基础信息 ===",
            f"robots.txt: {'存在' if self.basic and self.basic.robots_txt_exists else '不存在'}",
            f"sitemap: {'存在' if self.basic and self.basic.sitemap_urls else '不存在'}",
            f"RSS: {'存在' if self.basic and self.basic.rss_urls else '不存在'}",
            f"API文档: {'存在' if self.basic and self.basic.api_docs else '不存在'}",
            "",
            "=== 数据结构 ===",
            f"Schema.org: {len(self.data_struct.schema_org) if self.data_struct and self.data_struct.schema_org else '未检测到'}",
            f"Open Graph: {len(self.data_struct.opengraph) if self.data_struct and self.data_struct.opengraph else '未检测到'}",
            f"Twitter Cards: {len(self.data_struct.twitter) if self.data_struct and self.data_struct.twitter else '未检测到'}",
            f"自定义模式: {list(self.data_struct.custom_patterns.keys()) if self.data_struct and self.data_struct.custom_patterns else '未检测到'}",
            "",
            "=== 技术栈 ===",
            f"框架: {self.tech_stack.framework if self.tech_stack else 'unknown'}",
            f"动态渲染: {'是' if self.tech_stack and self.tech_stack.dynamic_rendering else '否'}",
            f"WAF/CDN: {self.tech_stack.cdn_waf if self.tech_stack else 'unknown'}",
            f"验证码: {', '.join(self.tech_stack.captcha) if self.tech_stack and self.tech_stack.captcha else '无'}",
            "",
            "=== 反爬特征 ===",
            f"User-Agent检查: {self.anti_spider.user_agent_check if self.anti_spider else 'unknown'}",
            f"频率限制: {'触发' if self.anti_spider and self.anti_spider.rate_limit_triggered else '未触发'}",
            f"JS挑战: {'是' if self.anti_spider and self.anti_spider.js_challenge else '否'}",
            "",
            "=== 综合评估 ===",
            f"难度: {self.assessment.difficulty if self.assessment else 'unknown'}",
            f"推荐工具: {self.assessment.recommended_tool if self.assessment else ''}",
            f"风险: {', '.join(self.assessment.key_risks) if self.assessment and self.assessment.key_risks else '无'}",
        ]
        return "\n".join(lines)

    def compare(self, other: 'CrawlFeasibilityResult') -> dict:
        """
        Compare this result with another result.
        Returns a dictionary describing differences.
        """
        comparison = {
            "url_changed": self.url != other.url,
            "timestamp_changed": self.timestamp != other.timestamp,
            "basic": self._compare_basic(self.basic, other.basic) if self.basic and other.basic else {"missing": True},
            "tech_stack": self._compare_tech_stack(self.tech_stack, other.tech_stack) if self.tech_stack and other.tech_stack else {"missing": True},
            "anti_spider": self._compare_anti_spider(self.anti_spider, other.anti_spider) if self.anti_spider and other.anti_spider else {"missing": True},
            "data_struct": self._compare_data_struct(self.data_struct, other.data_struct) if self.data_struct and other.data_struct else {"missing": True},
            "assessment": self._compare_assessment(self.assessment, other.assessment) if self.assessment and other.assessment else {"missing": True},
        }
        return comparison

    def _compare_basic(self, a: BasicResult, b: BasicResult) -> dict:
        diff = {}
        if a.robots_txt_exists != b.robots_txt_exists:
            diff["robots_txt_exists"] = {"old": b.robots_txt_exists, "new": a.robots_txt_exists}
        if a.robots_txt_content != b.robots_txt_content:
            diff["robots_txt_content"] = {"old": b.robots_txt_content, "new": a.robots_txt_content}
        if a.robots_txt_full_disallow != b.robots_txt_full_disallow:
            diff["robots_txt_full_disallow"] = {"old": b.robots_txt_full_disallow, "new": a.robots_txt_full_disallow}
        # For lists, we can compute added/removed
        if set(a.sitemap_urls) != set(b.sitemap_urls):
            diff["sitemap_urls"] = {
                "added": list(set(a.sitemap_urls) - set(b.sitemap_urls)),
                "removed": list(set(b.sitemap_urls) - set(a.sitemap_urls))
            }
        if a.html_sitemap != b.html_sitemap:
            diff["html_sitemap"] = {"old": b.html_sitemap, "new": a.html_sitemap}
        if set(a.rss_urls) != set(b.rss_urls):
            diff["rss_urls"] = {
                "added": list(set(a.rss_urls) - set(b.rss_urls)),
                "removed": list(set(b.rss_urls) - set(a.rss_urls))
            }
        if set(a.api_docs) != set(b.api_docs):
            diff["api_docs"] = {
                "added": list(set(a.api_docs) - set(b.api_docs)),
                "removed": list(set(b.api_docs) - set(a.api_docs))
            }
        if a.legal_notice != b.legal_notice:
            diff["legal_notice"] = {"old": b.legal_notice, "new": a.legal_notice}
        return diff

    def _compare_tech_stack(self, a: TechStackResult, b: TechStackResult) -> dict:
        diff = {}
        if a.framework != b.framework:
            diff["framework"] = {"old": b.framework, "new": a.framework}
        if a.dynamic_rendering != b.dynamic_rendering:
            diff["dynamic_rendering"] = {"old": b.dynamic_rendering, "new": a.dynamic_rendering}
        if a.content_loading != b.content_loading:
            diff["content_loading"] = {"old": b.content_loading, "new": a.content_loading}
        if a.cdn_waf != b.cdn_waf:
            diff["cdn_waf"] = {"old": b.cdn_waf, "new": a.cdn_waf}
        # captcha list
        if set(a.captcha) != set(b.captcha):
            diff["captcha"] = {
                "added": list(set(a.captcha) - set(b.captcha)),
                "removed": list(set(b.captcha) - set(a.captcha))
            }
        if a.fingerprinting != b.fingerprinting:
            diff["fingerprinting"] = {"old": b.fingerprinting, "new": a.fingerprinting}
        return diff

    def _compare_anti_spider(self, a: AntiSpiderResult, b: AntiSpiderResult) -> dict:
        diff = {}
        if a.default_status_code != b.default_status_code:
            diff["default_status_code"] = {"old": b.default_status_code, "new": a.default_status_code}
        if a.default_response_length != b.default_response_length:
            diff["default_response_length"] = {"old": b.default_response_length, "new": a.default_response_length}
        if a.default_redirect != b.default_redirect:
            diff["default_redirect"] = {"old": b.default_redirect, "new": a.default_redirect}
        if a.user_agent_check != b.user_agent_check:
            diff["user_agent_check"] = {"old": b.user_agent_check, "new": a.user_agent_check}
        if a.referer_check != b.referer_check:
            diff["referer_check"] = {"old": b.referer_check, "new": a.referer_check}
        if a.cookie_dependency != b.cookie_dependency:
            diff["cookie_dependency"] = {"old": b.cookie_dependency, "new": a.cookie_dependency}
        if a.rate_limit_triggered != b.rate_limit_triggered:
            diff["rate_limit_triggered"] = {"old": b.rate_limit_triggered, "new": a.rate_limit_triggered}
        if a.rate_limit_threshold != b.rate_limit_threshold:
            diff["rate_limit_threshold"] = {"old": b.rate_limit_threshold, "new": a.rate_limit_threshold}
        if a.captcha_trigger != b.captcha_trigger:
            diff["captcha_trigger"] = {"old": b.captcha_trigger, "new": a.captcha_trigger}
        if a.js_challenge != b.js_challenge:
            diff["js_challenge"] = {"old": b.js_challenge, "new": a.js_challenge}
        return diff

    def _compare_assessment(self, a: AssessmentResult, b: AssessmentResult) -> dict:
        diff = {}
        if a.difficulty != b.difficulty:
            diff["difficulty"] = {"old": b.difficulty, "new": a.difficulty}
        if a.recommended_tool != b.recommended_tool:
            diff["recommended_tool"] = {"old": b.recommended_tool, "new": a.recommended_tool}
        # key_risks list
        if set(a.key_risks) != set(b.key_risks):
            diff["key_risks"] = {
                "added": list(set(a.key_risks) - set(b.key_risks)),
                "removed": list(set(b.key_risks) - set(a.key_risks))
            }
        if a.code_template != b.code_template:
            diff["code_template"] = {"old": b.code_template, "new": a.code_template}
        if a.legal_note != b.legal_note:
            diff["legal_note"] = {"old": b.legal_note, "new": a.legal_note}
        return diff

    def _compare_data_struct(self, a: DataStructResult, b: DataStructResult) -> dict:
        diff = {}
        # For each field, compute added/removed if lists/dicts
        # schema_org list of dicts - we can compare by converting to tuple of items for simplicity
        if a.schema_org != b.schema_org:
            diff["schema_org"] = {
                "added": [item for item in a.schema_org if item not in b.schema_org],
                "removed": [item for item in b.schema_org if item not in a.schema_org]
            }
        if a.opengraph != b.opengraph:
            diff["opengraph"] = {
                "added": [item for item in a.opengraph if item not in b.opengraph],
                "removed": [item for item in b.opengraph if item not in a.opengraph]
            }
        if a.twitter != b.twitter:
            diff["twitter"] = {
                "added": [item for item in a.twitter if item not in b.twitter],
                "removed": [item for item in b.twitter if item not in a.twitter]
            }
        if a.custom_patterns != b.custom_patterns:
            diff["custom_patterns"] = {
                "added": {k: a.custom_patterns[k] for k in set(a.custom_patterns) - set(b.custom_patterns)},
                "removed": {k: b.custom_patterns[k] for k in set(b.custom_patterns) - set(a.custom_patterns)}
            }
        return diff
