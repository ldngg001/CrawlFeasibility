"""
Web interface for CrawlFeasibility - Cloudflare Pages compatible version
"""
import asyncio
import json
import os
from flask import Flask, request, jsonify

app = Flask(__name__)

def run_async(coro):
    """Helper to run async functions in Flask"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


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


@app.route('/')
def index():
    """Health check endpoint"""
    return jsonify({"status": "ok", "service": "CrawlFeasibility"})


@app.route('/scan', methods=['POST'])
def scan():
    """执行扫描"""
    try:
        data = request.get_json()
    except Exception:
        data = {}
    
    url = data.get('url') if data else None
    deep = data.get('deep', False) if data else False
    
    if not url:
        return jsonify({'error': 'URL is required'}), 400
    
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url
    
    try:
        result = run_async(perform_detection(url, deep))
        return jsonify(result.to_dict())
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/scan', methods=['POST'])
def api_scan():
    """Alias for /scan for Cloudflare Pages API compatibility"""
    return scan()


# Cloudflare Pages uses this
def handler(request):
    """Handle requests for Cloudflare Pages"""
    method = request.method
    path = request.path
    
    if path == '/' and method == 'GET':
        return index()
    elif path == '/scan' and method == 'POST':
        return scan()
    elif path == '/api/scan' and method == 'POST':
        return api_scan()
    else:
        return jsonify({"error": "Not found"}), 404