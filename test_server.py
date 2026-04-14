"""
Simple local test server to mimic Cloudflare Pages Functions
"""
from http.server import HTTPServer, BaseHTTPRequestHandler
import json

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/' or self.path == '/index.html':
            with open('public/index.html', 'r', encoding='utf-8') as f:
                self.send_response(200)
                self.send_header('Content-Type', 'text/html')
                self.end_headers()
                self.wfile.write(f.read().encode())
        else:
            self.send_response(404)
            self.end_headers()
    
    def do_POST(self):
        if self.path == '/scan':
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length) if content_length > 0 else b'{}'
            
            try:
                data = json.loads(body)
            except:
                data = {}
            
            url = data.get('url', '')
            deep = data.get('deep', False)
            
            # Simulate response (will fail since we don't have Python libs in Cloudflare)
            result = {
                "url": url,
                "timestamp": "2026-04-14T00:00:00",
                "basic": {"robots_txt_exists": False, "sitemap_urls": [], "rss_urls": [], "api_docs": []},
                "tech_stack": {"framework": "Unknown", "dynamic_rendering": False, "cdn_waf": "None", "captcha": []},
                "anti_spider": {"user_agent_check": "Not Detected", "referer_check": "Not Detected", "cookie_dependency": "None", "rate_limit_triggered": False, "js_challenge": False},
                "assessment": {"difficulty": "low", "recommended_tool": "requests", "key_risks": [], "code_template": "import requests", "legal_note": "Test"}
            }
            
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(result).encode())
        else:
            self.send_response(404)
            self.end_headers()

print("Starting test server at http://127.0.0.1:8787")
HTTPServer(('127.0.0.1', 8787), Handler).serve_forever()