"""数据结构检测模块"""
import re
from typing import List, Dict, Any
from bs4 import BeautifulSoup, Comment

from src.crawler.base_checker import BaseChecker


class DataStructureChecker(BaseChecker):
    """检测网页中的结构化数据"""

    async def check(self, url: str) -> 'DataStructResult':
        """执行数据结构检测"""
        # 获取页面内容
        response = await self.client.get(url)
        if not response:
            return DataStructResult(
                schema_org=[],
                opengraph=[],
                twitter=[],
                custom_patterns={}
            )

        html = response.text
        soup = BeautifulSoup(html, 'html.parser')

        # 初始化结果容器
        schema_org: List[Dict[str, Any]] = []
        opengraph: List[Dict[str, Any]] = []
        twitter: List[Dict[str, Any]] = []
        custom_patterns: Dict[str, List[str]] = {
            'price': [],
            'date': [],
            'email': [],
            'phone': []
        }

        # 1. 检测 Schema.org (JSON-LD, Microdata, RDFa)
        # JSON-LD
        for script in soup.find_all('script', type='application/ld+json'):
            try:
                import json
                data = json.loads(script.string or '')
                if isinstance(data, dict) and '@type' in data:
                    schema_org.append({
                        'type': 'JSON-LD',
                        'schema_type': data['@type'],
                        'snippet': str(data)[:200]
                    })
                elif isinstance(data, list):
                    for item in data:
                        if isinstance(item, dict) and '@type' in item:
                            schema_org.append({
                                'type': 'JSON-LD',
                                'schema_type': item['@type'],
                                'snippet': str(item)[:200]
                            })
            except Exception:
                pass

        # Microdata (itemscope, itemtype)
        for element in soup.find_all(itemscope=True):
            itemtype = element.get('itemtype')
            if itemtype and 'schema.org' in itemtype:
                schema_type = itemtype.split('/')[-1]
                schema_org.append({
                    'type': 'Microdata',
                    'schema_type': schema_type,
                    'snippet': element.get_text()[:200]
                })

        # RDFa (typeof, property)
        for element in soup.find_all(typeof=True):
            typeof = element.get('typeof')
            if typeof and 'schema.org' in typeof:
                schema_type = typeof.split('/')[-1]
                schema_org.append({
                    'type': 'RDFa',
                    'schema_type': schema_type,
                    'snippet': element.get_text()[:200]
                })

        # 2. 检测 Open Graph
        for meta in soup.find_all('meta', property=re.compile(r'^og:')):
            property_name = meta.get('property')
            content = meta.get('content', '')
            opengraph.append({
                'property': property_name,
                'content': content[:200]
            })

        # 3. 检测 Twitter Cards
        for meta in soup.find_all('meta', attrs={'name': re.compile(r'^twitter:')}):
            name = meta.get('name')
            content = meta.get('content', '')
            twitter.append({
                'name': name,
                'content': content[:200]
            })

        # 4. 检测自定义模式
        text = soup.get_text()

        # 价格模式（支持 $, ￥, €, £ 等）
        price_pattern = r'(?:[\$\￥€£]\s*)?\d+(?:[.,]\d+)*(?:\s*[USD|EUR|GBP|CNY|JPY]+)?'
        prices = re.findall(price_pattern, text, re.IGNORECASE)
        custom_patterns['price'] = list(set(prices))[:10]  # 去重并限制数量

        # 日期模式（简化）
        date_patterns = [
            r'\d{4}[-/]\d{1,2}[-/]\d{1,2}',
            r'\d{1,2}[-/]\d{1,2}[-/]\d{4}',
            r'\d{1,2}\s*(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s*\d{2,4}',
            r'(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s*\d{1,2},?\s*\d{4}'
        ]
        dates = []
        for pattern in date_patterns:
            dates.extend(re.findall(pattern, text, re.IGNOREDATE))
        custom_patterns['date'] = list(set(dates))[:10]

        # 邮箱
        email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
        emails = re.findall(email_pattern, text)
        custom_patterns['email'] = list(set(emails))[:10]

        # 电话（简化，支持常见格式）
        phone_pattern = r'(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}'
        phones = re.findall(phone_pattern, text)
        custom_patterns['phone'] = list(set(phones))[:10]

        return DataStructResult(
            schema_org=schema_org,
            opengraph=opengraph,
            twitter=twitter,
            custom_patterns=custom_patterns
        )


from src.models.result import BasicResult, TechStackResult, AntiSpiderResult, AssessmentResult, CrawlFeasibilityResult


@dataclass
class DataStructResult:
    """数据结构检测结果"""
    schema_org: List[Dict[str, Any]] = field(default_factory=list)
    opengraph: List[Dict[str, Any]] = field(default_factory=list)
    twitter: List[Dict[str, Any]] = field(default_factory=list)
    custom_patterns: Dict[str, List[str]] = field(default_factory=dict)

    def to_dict(self):
        return asdict(self)