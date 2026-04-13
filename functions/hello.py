"""
Cloudflare Pages Function - Python
"""
import asyncio
import json
from dataclasses import dataclass


@dataclass
class Response:
    """Simple Response for Cloudflare Pages"""
    def __init__(self, body, status=200, content_type='application/json'):
        self.body = body
        self.status = status
        self.content_type = content_type
    
    @staticmethod
    def json(data, status=200):
        return Response(json.dumps(data), status, 'application/json')


async def async_perform_detection(url, deep=False):
    """执行检测并返回结果"""
    from src.crawler import BasicChecker, TechStackChecker, AntiSpiderChecker, Assessor
    from src.models.result import CrawlFeasibilityResult
    from src.utils.http_client import HttpClient
    
    client = HttpClient()
    
    basic_checker = BasicChecker(client)
    tech_checker = TechStackChecker(client)
    anti_checker = AntiSpiderChecker(client, deep=deep)
    assessor = Assessor()
    
    basic_result = await basic_checker.check(url)
    tech_result = await tech_checker.check(url)
    anti_result = await anti_checker.check(url)
    assessment_result = assessor.assess(basic_result, tech_result, anti_result)
    
    result = CrawlFeasibilityResult(
        url=url,
        basic=basic_result,
        tech_stack=tech_result,
        anti_spider=anti_result,
        assessment=assessment_result,
    )
    
    client.close()
    return result


def on_request(request):
    """Handle requests for Cloudflare Pages"""
    
    if request.path == "/" and request.method == "GET":
        return {"status": "ok", "service": "CrawlFeasibility"}
    
    if request.path == "/scan" and request.method == "POST":
        try:
            try:
                data = request.json()
            except:
                data = {}
            
            url = data.get("url")
            deep = data.get("deep", False)
            
            if not url:
                return {"error": "URL is required"}
            
            if not url.startswith(("http://", "https://")):
                url = "https://" + url
            
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    result = loop.run_until_complete(async_perform_detection(url, deep))
                    return result.to_dict()
                finally:
                    loop.close()
            except Exception as e:
                return {"error": str(e)}
        except Exception as e:
            return {"error": str(e)}
    
    return {"error": "Not found"}