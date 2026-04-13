"""
Web interface for CrawlFeasibility - Cloudflare Pages compatible version
"""
import asyncio
import json

async def perform_detection(url, deep=False):
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
    
    return result


def run_async(coro):
    """Helper to run async functions"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


def handler(request):
    """Cloudflare Pages handler function"""
    method = request.method
    path = request.path
    
    if path == '/' and method == 'GET':
        return Response(json.dumps({"status": "ok", "service": "CrawlFeasibility"}), 
                       mimetype='application/json')
    
    elif path == '/scan' and method == 'POST':
        try:
            try:
                data = json.loads(request.text)
            except:
                data = {}
            
            url = data.get('url') if data else None
            deep = data.get('deep', False) if data else False
            
            if not url:
                return Response(json.dumps({'error': 'URL is required'}), 
                             status=400, mimetype='application/json')
            
            if not url.startswith(('http://', 'https://')):
                url = 'https://' + url
            
            try:
                result = run_async(perform_detection(url, deep))
                return Response(json.dumps(result.to_dict()), 
                             mimetype='application/json')
            except Exception as e:
                return Response(json.dumps({'error': str(e)}), 
                             status=500, mimetype='application/json')
        except Exception as e:
            return Response(json.dumps({'error': str(e)}), 
                         status=500, mimetype='application/json')
    
    elif path == '/api/scan' and method == 'POST':
        try:
            try:
                data = json.loads(request.text)
            except:
                data = {}
            
            url = data.get('url') if data else None
            deep = data.get('deep', False) if data else False
            
            if not url:
                return Response(json.dumps({'error': 'URL is required'}), 
                             status=400, mimetype='application/json')
            
            if not url.startswith(('http://', 'https://')):
                url = 'https://' + url
            
            try:
                result = run_async(perform_detection(url, deep))
                return Response(json.dumps(result.to_dict()), 
                             mimetype='application/json')
            except Exception as e:
                return Response(json.dumps({'error': str(e)}), 
                             status=500, mimetype='application/json')
        except Exception as e:
            return Response(json.dumps({'error': str(e)}), 
                         status=500, mimetype='application/json')
    
    else:
        return Response(json.dumps({"error": "Not found"}), 
                     status=404, mimetype='application/json')


class Response:
    """Simple response wrapper for Cloudflare Pages"""
    def __init__(self, body, status=200, mimetype='text/html'):
        self.body = body
        self.status = status
        self.mimetype = mimetype
    
    def __call__(self, environ, start_response):
        start_response(str(self.status), [('Content-Type', self.mimetype)])
        return [self.body.encode()]