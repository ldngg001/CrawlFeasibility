/**
 * Cloudflare Pages Function - JavaScript
 */

export async function onRequestPost(context) {
  const { request } = context;
  
  try {
    const data = await request.json();
  } catch {
    return new Response(JSON.stringify({ error: "Invalid JSON" }), {
      status: 400,
      headers: { "Content-Type": "application/json" }
    });
  }
  
  const url = data.url;
  const deep = data.deep || false;
  
  if (!url) {
    return new Response(JSON.stringify({ error: "URL is required" }), {
      status: 400,
      headers: { "Content-Type": "application/json" }
    });
  }
  
  let targetUrl = url;
  if (!targetUrl.startsWith("http://") && !targetUrl.startsWith("https://")) {
    targetUrl = "https://" + targetUrl;
  }
  
  // 导入检测模块并执行检测
  // 由于 Cloudflare Workers 环境限制，这里使用简化的检测逻辑
  const result = await performDetection(targetUrl, deep);
  
  return new Response(JSON.stringify(result), {
    headers: { "Content-Type": "application/json" }
  });
}

export async function onRequest(context) {
  return new Response(JSON.stringify({ status: "ok", service: "CrawlFeasibility" }), {
    headers: { "Content-Type": "application/json" }
  });
}

async function performDetection(url, deep) {
  // 简化的检测逻辑 - 实际部署需要后端服务支持
  const client = typeof fetch !== 'undefined' ? fetch : null;
  
  try {
    // 基础检测
    const response = await fetch(url, {
      method: "GET",
      headers: {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
      }
    });
    
    const html = await response.text();
    
    // 检测 robots.txt
    const robotsUrl = new URL("/robots.txt", url).href;
    let robotsTxtExists = false;
    try {
      const robotsResponse = await fetch(robotsUrl, { method: "HEAD" });
      robotsTxtExists = robotsResponse.ok;
    } catch {}
    
    // 检测框架
    let framework = "static";
    if (html.includes("react") || html.includes("React")) framework = "react";
    else if (html.includes("vue") || html.includes("Vue")) framework = "vue";
    else if (html.includes("angular")) framework = "angular";
    
    // 检测动态渲染
    const dynamicRendering = html.length < 500 || html.includes("data-reactroot") || html.includes("ng-app");
    
    // 评估难度
    let difficulty = "low";
    let recommendedTool = "requests + BeautifulSoup";
    
    if (dynamicRendering || framework !== "static") {
      difficulty = "medium";
      recommendedTool = "Playwright / Selenium";
    }
    
    if (html.includes("cloudflare") || html.includes("captcha")) {
      difficulty = "high";
      recommendedTool = "Selenium + CAPTCHA solver";
    }
    
    return {
      url: url,
      timestamp: new Date().toISOString(),
      basic: {
        robots_txt_exists: robotsTxtExists,
        sitemap_urls: [],
        rss_urls: [],
        api_docs: [],
        html_sitemap: false,
        legal_notice: false
      },
      tech_stack: {
        framework: framework,
        cdn_waf: html.includes("cloudflare") ? "cloudflare" : "none",
        captcha: [],
        fingerprinting: false,
        dynamic_rendering: dynamicRendering,
        content_loading: dynamicRendering ? "client-side" : "server-side"
      },
      anti_spider: {
        user_agent_check: "pass",
        referer_check: "pass",
        cookie_dependency: "unknown",
        rate_limit_triggered: false,
        js_challenge: html.includes("checking your browser")
      },
      assessment: {
        difficulty: difficulty,
        recommended_tool: recommendedTool,
        key_risks: [],
        code_template: getCodeTemplate(difficulty),
        legal_note: "Please respect robots.txt and rate limits. Do not crawl without permission."
      }
    };
  } catch (error) {
    return {
      url: url,
      error: error.message,
      timestamp: new Date().toISOString()
    };
  }
}

function getCodeTemplate(difficulty) {
  if (difficulty === "high") {
    return `from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from anticaptchaimport import AnticaptchaTask

driver = webdriver.Chrome()
driver.get("YOUR_URL")
# Handle CAPTCHA if present
wait = WebDriverWait(driver, 10)
element = wait.until(EC.presence_of_element_located((By.ID, "content")))`;
  } else if (difficulty === "medium") {
    return `from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page()
    page.goto("YOUR_URL")
    content = page.content()
    browser.close()`;
  } else {
    return `import requests
from bs4 import BeautifulSoup

response = requests.get("YOUR_URL", headers={"User-Agent": "Mozilla/5.0"})
soup = BeautifulSoup(response.text, "lxml")
links = soup.find_all("a")`;
  }
}