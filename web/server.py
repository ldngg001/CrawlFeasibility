"""
Web server for CrawlFeasibility - Flask
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

import asyncio
import json
from flask import Flask, request, jsonify, send_from_directory
from pathlib import Path

import os
app = Flask(__name__, static_folder=os.path.join(os.path.dirname(__file__), '..', 'public'), static_url_path='')

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
    
    client.close()
    return result


@app.route('/')
def index():
    """Serve the HTML page"""
    public_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'public')
    with open(os.path.join(public_dir, 'index.html'), 'r', encoding='utf-8') as f:
        return f.read()


@app.route('/scan', methods=['POST'])
def scan():
    """执行扫描"""
    try:
        try:
            data = request.get_json()
        except:
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
    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000, debug=True)