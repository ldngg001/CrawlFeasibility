# CrawlFeasibility Detection Rules

This document details the detection rules used in CrawlFeasibility for each module.

## 1. Basic Information Checker

### robots.txt
- Paths checked: `/robots.txt`
- Rules:
  - If found (HTTP 200), content is stored.
  - Full disallow check: looks for a `User-agent:` block (any) with `Disallow: /`.
    - Note: This is a simplified check; real robots.txt may have multiple user-agents.
- Output:
  - `robots_txt_exists`: boolean
  - `robots_txt_content`: string (if exists)
  - `robots_txt_full_disallow`: boolean

### sitemap.xml
- Paths checked:
  - `/sitemap.xml`
  - `/sitemap_index.xml`
  - `/sitemap1.xml`
  - `/sitemap2.xml`
- Additionally, if `robots.txt` exists, lines starting with `Sitemap:` are parsed.
- Output: list of found sitemap URLs.

### HTML Sitemap
- Checks for `<link rel="sitemap">` in the HTML head.
- Also checks for an anchor (`<a>`) containing the text "sitemap" (case-insensitive).
- Output: boolean.

### RSS/Atom Feeds
- Paths checked:
  - `/feed`
  - `/rss`
  - `/feed.xml`
  - `/rss.xml`
  - `/atom.xml`
  - `/atom`
- For each path, if the response is HTTP 200 and Content-Type contains `xml`, `rss`, or `atom`, it's considered a feed.
- Output: list of found feed URLs.

### API Documentation
- Patterns scanned in HTML (case-insensitive):
  - `/api`
  - `/swagger`
  - `/docs`
  - `/documentation`
  - `/api-docs`
- Also scans for anchors with `href` containing `/api/` or `/api`.
- Output: list of absolute URLs to API documentation.

### Legal Notice (Anti-crawling)
- Scans the HTML text (lowercase) for regex patterns:
  - `禁止.*爬取`
  - `禁止.*采集`
  - `禁止.*抓取`
  - `robots?.*denied`
  - `no\s*robots?`
  - `copyright.*all\s*rights?\s*reserved`
- Output: boolean (True if any pattern found).

## 2. Technology Stack Checker

### Framework Detection
- Uses fingerprint library (see `src/utils/fingerprint.py`).
- Looks for signatures in HTML and JavaScript:
  - React: `react`, `react-dom`, `data-reactroot`
  - Vue: `vue.js`, `data-v-`, `__vue__`
  - Angular: `angular`, `ng-app`, `ng-version`
  - etc.
- Output: string (framework name) or "static" if none detected.

### WAF/CDN Detection
- Checks response headers and HTML body for signatures:
  - Cloudflare: `__cf_bm`, `cloudflare`, `cf-ray`
  - Alibaba Cloud: `aliyun`, `waf.aliyuncs.com`
  - AWS CloudFront: `cloudfront`, `x-amz-cf-id`, `x-amz-cf-pop`
  - etc.
- Output: string (WAF/CDN name) or "none".

### CAPTCHA Detection
- Looks for known CAPTCHA provider signatures in HTML:
  - reCAPTCHA: `recaptcha`, `grecaptcha`
  - hCaptcha: `hcaptcha`
  - Geetest: `geetest`
  - etc.
- Output: list of detected CAPTCHA providers.

### Browser Fingerprinting
- Checks for common fingerprinting techniques in JavaScript:
  - Navigator properties: `navigator.languages`, `navigator.plugins`, `navigator.mimeTypes`
  - Canvas fingerprinting: `canvas.toDataURL`
  - WebGL fingerprinting: `webgl.getExtension`
  - etc.
- Output: boolean.

### Dynamic Rendering Detection
- Heuristics:
  - If the visible text length (from `<body>`) is less than 100 characters -> likely dynamic.
  - If the body contains loading indicators: `loading`, `spinner`, `skeleton`, `placeholder`.
  - If the body contains framework-specific root attributes: `data-reactroot`, `data-v-`, `ng-app`, `id="app"`, `id="root"`.
- Output: boolean.

### Content Loading Way
- Determines how content is loaded:
  - Client-side: if there are multiple AJAX/fetch calls in the JavaScript (`fetch(`, `axios.`, `$.ajax`, `XMLHttpRequest`, `async`, `await fetch`).
  - SSR: if there is JSON-LD (`<script type="application/ld+json">`).
  - Otherwise: server-side.
- Output: string ("client-side", "ssr", "server-side").

## 3. Anti-Spider Feature Checker

### Default Response
- Records:
  - Status code
  - Response body length
  - Redirect URL (if any)

### User-Agent Check
- Sends a request without a User-Agent header (or with an empty one).
- If the response status is 403 or 406 -> considered a failure (UA required).
- Output: string ("pass", "fail", "unknown").

### Referer Check
- Sends a request to a resource (usually the same URL) without a Referer header.
- If the response status is 403 or 406 -> considered a failure (Referer required).
- Output: string ("pass", "fail", "unknown").

### Cookie Dependency
- Makes two requests:
  1. Normal request to get cookies.
  2. Second request with all cookies cleared.
- If the response status or final URL changes (e.g., redirects to login) -> Cookie dependent.
- Output: string ("yes", "no", "unknown").

### Rate Limit Test
- Sends multiple requests with increasing frequency:
  - Basic mode: intervals [1.0, 0.5, 0.3, 0.2, 0.2] seconds (5 requests).
  - Deep mode: intervals [1.0, 0.8, 0.6, 0.4, 0.2, 0.2, 0.2, 0.2, 0.2, 0.2] seconds (10 requests).
- If any response returns 429 (Too Many Requests) or 503 (Service Unavailable) -> rate limit triggered.
- Also considers any non-200 response as a potential trigger (conservative).
- Output: dict with `triggered` (boolean) and `threshold` (string describing when triggered).

### CAPTCHA Trigger
- Makes up to 3 requests, each time checking the response text (lowercase) for CAPTCHA indicators:
  - `captcha`, `recaptcha`, `hcaptcha`, `turnstile`, `verify you're human`, `请验证`, `验证`.
- Waits 1 second between requests.
- Output: boolean.

### JavaScript Challenge (e.g., Cloudflare)
- Checks the response text (lowercase) for known challenge indicators:
  - `checking your browser`
  - `please wait`
  - `just a moment`
  - `cloudflare`
  - `access denied`
  - `ddos-guard`
  - `security check`
- Also checks for status 403/503 with Cloudflare indicators (`cf-ray` in headers or `cloudflare` in text).
- Output: boolean.

## Notes
- All checks are performed with a configurable timeout (default 10 seconds).
- User-Agent: by default, a random realistic browser UA is used to avoid being blocked as a bot.
- Deep mode enables more aggressive rate limiting and CAPTCHA triggering tests (more requests).
- Errors during individual checks are caught and logged, and the check returns a default value (e.g., False, empty list) so that the overall assessment can proceed.
