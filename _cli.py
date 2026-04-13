"""
Cloudflare Pages entry point
"""
import sys
import os

# Add current directory to path
sys.path.insert(0, os.path.dirname(__file__))

from web.app import app

def handler(event, context):
    """Cloudflare Pages handler function"""
    return app(event, context)