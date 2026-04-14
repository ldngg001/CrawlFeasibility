/**
 * Cloudflare Pages Function for CrawlFeasibility /scan endpoint
 */

export async function onRequestPost(context) {
  const { request } = context;
  
  try {
    // Parse request body
    let data;
    try {
      data = await request.json();
    } catch {
      data = {};
    }
    
    const url = data?.url;
    const deep = data?.deep || false;
    
    if (!url) {
      return new Response(JSON.stringify({ error: "URL is required" }), {
        status: 400,
        headers: { "Content-Type": "application/json" }
      });
    }
    
    // Add scheme if missing
    let targetUrl = url;
    if (!url.startsWith('http://') && !url.startsWith('https://')) {
      targetUrl = 'https://' + url;
    }
    
    // Run detection
    const result = await runDetection(targetUrl, deep);
    
    return new Response(JSON.stringify(result), {
      status: 200,
      headers: { "Content-Type": "application/json" }
    });
    
  } catch (error) {
    return new Response(JSON.stringify({ 
      error: `${error.constructor.name}: ${error.message}`,
      stack: error.stack 
    }), {
      status: 500,
      headers: { "Content-Type": "application/json" }
    });
  }
}

async function runDetection(url, deep) {
  // Use fetch to make HTTP requests
  const client = new HttpClient();
  
  // Run checks in parallel where possible
  const [basicResult, techResult] = await Promise.all([
    checkBasic(client, url),
    checkTechStack(client, url)
  ]);
  
  const antiResult = await checkAntiSpider(client, url, deep);
  const assessment = assess(basicResult, techResult, antiResult);
  
  return {
    url,
    timestamp: new Date().toISOString(),
    basic: basicResult,
    tech_stack: techResult,
    anti_spider: antiResult,
    assessment
  };
}

async function checkBasic(client, url) {
  const results = {
    robots_txt_exists: false,
    sitemap_urls: [],
    rss_urls: [],
    api_docs: []
  };
  
  try {
    const parsedUrl = new URL(url);
    const baseUrl = `${parsedUrl.protocol}//${parsedUrl.host}`;
    
    // Check robots.txt
    try {
      const robotsResp = await client.fetch(`${baseUrl}/robots.txt`);
      results.robots_txt_exists = robotsResp.ok;
    } catch {}
    
    // Check sitemap.xml
    try {
      const sitemapResp = await client.fetch(`${baseUrl}/sitemap.xml`);
      if (sitemapResp.ok) {
        results.sitemap_urls.push(`${baseUrl}/sitemap.xml`);
      }
    } catch {}
    
    // Check common sitemap locations
    const sitemapPaths = ['/sitemap_index.xml', '/sitemap-index.xml', '/sitemap1.xml'];
    for (const path of sitemapPaths) {
      try {
        const resp = await client.fetch(`${baseUrl}${path}`);
        if (resp.ok && !results.sitemap_urls.includes(`${baseUrl}${path}`)) {
          results.sitemap_urls.push(`${baseUrl}${path}`);
        }
      } catch {}
    }
    
    // Check RSS/Atom feeds
    const feedPaths = ['/feed', '/rss', '/atom.xml', '/feed.xml', '/blog/feed'];
    for (const path of feedPaths) {
      try {
        const resp = await client.fetch(`${baseUrl}${path}`);
        if (resp.ok) {
          results.rss_urls.push(`${baseUrl}${path}`);
        }
      } catch {}
    }
    
    // Check API docs
    const apiPaths = ['/api', '/docs', '/api-docs', '/developer', '/api/docs'];
    for (const path of apiPaths) {
      try {
        const resp = await client.fetch(`${baseUrl}${path}`);
        if (resp.ok) {
          results.api_docs.push(`${baseUrl}${path}`);
        }
      } catch {}
    }
    
  } catch (error) {
    console.error('Basic check error:', error);
  }
  
  return results;
}

async function checkTechStack(client, url) {
  const results = {
    framework: 'Unknown',
    dynamic_rendering: false,
    cdn_waf: 'None',
    captcha: []
  };
  
  try {
    const resp = await client.fetch(url);
    const headers = resp.headers;
    const server = headers.get('server') || '';
    const poweredBy = headers.get('x-powered-by') || '';
    
    // Check for CDN/WAF
    const cdnWafIndicators = ['cloudflare', 'akamai', 'fastly', 'cloudfront', 'incapsula', 'imperva', 'sucuri'];
    for (const indicator of cdnWafIndicators) {
      const lowerCombined = (server + poweredBy).toLowerCase();
      if (lowerCombined.includes(indicator)) {
        results.cdn_waf = indicator.charAt(0).toUpperCase() + indicator.slice(1);
        break;
      }
    }
    
    // Check headers for tech stack
    const allHeaders = headers.toString().toLowerCase();
    
    // Detect framework
    if (allHeaders.includes('nextjs') || allHeaders.includes('__next')) {
      results.framework = 'Next.js';
      results.dynamic_rendering = true;
    } else if (allHeaders.includes('nuxt')) {
      results.framework = 'Nuxt.js';
      results.dynamic_rendering = true;
    } else if (allHeaders.includes('react')) {
      results.framework = 'React';
    } else if (allHeaders.includes('vue')) {
      results.framework = 'Vue.js';
    } else if (allHeaders.includes('angular')) {
      results.framework = 'Angular';
    }
    
    // Check for JS rendering indicators
    const html = await resp.text();
    if (html.includes('<!--') && html.includes('-->')) {
      // Could be hidden content for JS
      results.dynamic_rendering = true;
    }
    
  } catch (error) {
    console.error('Tech stack check error:', error);
  }
  
  return results;
}

async function checkAntiSpider(client, url, deep) {
  const results = {
    user_agent_check: 'Not Detected',
    referer_check: 'Not Detected',
    cookie_dependency: 'None',
    rate_limit_triggered: false,
    js_challenge: false
  };
  
  try {
    // Test without User-Agent
    const noUaResp = await client.fetch(url, { 
      headers: { 'User-Agent': '' }
    });
    
    if (noUaResp.status === 403 || noUaResp.status === 503) {
      results.user_agent_check = 'Required';
    }
    
    // Test without Referer
    const noRefResp = await client.fetch(url, {
      headers: { 'Referer': '' }
    });
    
    if (noRefResp.status === 403) {
      results.referer_check = 'Required';
    }
    
    // Check for Set-Cookie
    const setCookie = noUaResp.headers.get('set-cookie');
    if (setCookie) {
      results.cookie_dependency = 'Required';
    }
    
    // Deep scan - make multiple requests
    if (deep) {
      let blocked = false;
      for (let i = 0; i < 5; i++) {
        const testResp = await client.fetch(url);
        if (testResp.status === 429) {
          blocked = true;
          break;
        }
        await new Promise(r => setTimeout(r, 500));
      }
      results.rate_limit_triggered = blocked;
    }
    
  } catch (error) {
    console.error('Anti-spider check error:', error);
  }
  
  return results;
}

function assess(basic, tech, anti) {
  let difficulty = 'low';
  let score = 0;
  const risks = [];
  let recommendedTool = 'requests';
  
  // Score based on factors
  if (!basic.robots_txt_exists) score += 1;
  if (basic.sitemap_urls.length > 0) score -= 1;
  if (basic.api_docs.length > 0) score -= 2;
  
  if (tech.dynamic_rendering) {
    score += 2;
    recommendedTool = 'Playwright/Puppeteer';
  }
  
  if (tech.cdn_waf !== 'None') {
    score += 2;
    risks.push(`WAF/CDN detected (${tech.cdn_waf}) - may block requests`);
  }
  
  if (tech.captcha.length > 0) {
    score += 3;
    risks.push(`Captcha required: ${tech.captcha.join(', ')}`);
  }
  
  if (anti.user_agent_check === 'Required') score += 1;
  if (anti.referer_check === 'Required') score += 1;
  if (anti.cookie_dependency === 'Required') score += 1;
  if (anti.rate_limit_triggered) {
    score += 2;
    risks.push('Rate limiting detected - may block after threshold');
  }
  if (anti.js_challenge) {
    score += 2;
    risks.push('JS challenge detected - requires browser automation');
    recommendedTool = 'Playwright/Puppeteer';
  }
  
  // Determine difficulty
  if (score >= 6) difficulty = 'high';
  else if (score >= 3) difficulty = 'medium';
  
  // Build legal note
  const legalNote = `请遵守以下规范：
1. 遵守 robots.txt 规则（若存在）
2. 遵守目标网站的 Terms of Service
3. 合理控制请求频率，避免对服务器造成负担
4. 仅将获取的数据用于合法的学习研究目的
5. 尊重数据版权，不要传播或商用
6. 跨境数据采集需遵守当地法律法规`;
  
  // Code template
  let codeTemplate = '';
  if (recommendedTool === 'Playwright/Puppeteer') {
    codeTemplate = `from playwright.sync_api import sync_playwright

def crawl(url):
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto(url)
        content = page.content()
        browser.close()
        return content`;
  } else {
    codeTemplate = `import requests

def crawl(url):
    headers = {
        'User-Agent': 'Mozilla/5.0 (compatible; Bot/0.1)'
    }
    response = requests.get(url, headers=headers, timeout=10)
    return response.text`;
  }
  
  return {
    difficulty,
    recommended_tool: recommendedTool,
    key_risks: risks,
    code_template: codeTemplate,
    legal_note: legalNote
  };
}

// Simple HttpClient wrapper for fetch
class HttpClient {
  constructor(options = {}) {
    this.timeout = options.timeout || 10000;
    this.defaultHeaders = {
      'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    };
  }
  
  async fetch(url, options = {}) {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), this.timeout);
    
    try {
      const response = await fetch(url, {
        ...options,
        signal: controller.signal,
        headers: {
          ...this.defaultHeaders,
          ...options.headers
        }
      });
      return response;
    } finally {
      clearTimeout(timeoutId);
    }
  }
}