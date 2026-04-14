import { onRequestPost } from './functions/scan.js';

const INDEX_HTML = `<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>CrawlFeasibility - Web Crawlability Assessment</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdn.jsdelivr.net/npm/@mdi/font@6.x/css/materialdesignicons.min.css" rel="stylesheet">
    <style>
        body { background-color: #f8f9fa; }
        .container { margin-top: 2rem; }
        .result-card { margin-top: 2rem; box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1); }
        .risk-high { color: #dc3545; }
        .risk-medium { color: #fd7e14; }
        .risk-low { color: #198754; }
        .loading { display: none; text-align: center; padding: 2rem; }
        .result-section { margin-top: 1.5rem; }
        .btn-scan { width: 100%; padding: 1rem; font-size: 1.1rem; }
        .footer { margin-top: 3rem; padding-top: 2rem; border-top: 1px solid #dee2e6; color: #6c757d; font-size: 0.9rem; }
    </style>
</head>
<body>
    <div class="container">
        <div class="row justify-content-center">
            <div class="col-md-8">
                <div class="card">
                    <div class="card-header bg-primary text-white">
                        <h4 class="mb-0"><i class="mdi mdi-web-search me-2"></i>CrawlFeasibility - Web Crawlability Assessment</h4>
                    </div>
                    <div class="card-body">
                        <form id="scanForm">
                            <div class="mb-3">
                                <label for="urlInput" class="form-label">Target Website URL</label>
                                <div class="input-group">
                                    <input type="text" class="form-control" id="urlInput" placeholder="e.g., https://example.com" required>
                                    <button class="btn btn-outline-secondary" type="button" id="exampleBtn">Example</button>
                                </div>
                                <div class="form-text">We'll assess the website's crawler-friendliness and technical requirements</div>
                            </div>
                            <div class="mb-3 form-check">
                                <input type="checkbox" class="form-check-input" id="deepCheck">
                                <label class="form-check-label" for="deepCheck">Deep Scan (more requests, may trigger anti-bot defenses)</label>
                            </div>
                            <button type="submit" class="btn btn-primary btn-scan">
                                <i class="mdi mdi-magnify me-2"></i>Start Assessment
                            </button>
                        </form>
                        <div class="loading" id="loading">
                            <div class="spinner-border text-primary" role="status">
                                <span class="visually-hidden">Loading...</span>
                            </div>
                            <p class="mt-3">Assessing website, please wait...</p>
                        </div>
                        <div id="resultContainer" class="d-none">
                            <div class="result-card">
                                <div class="card-body">
                                    <div id="resultContent"></div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>
    <div class="footer">
        <div class="container text-center">
            <p>© 2026 CrawlFeasibility. For technical research and learning purposes only. Please comply with applicable laws and terms of service.</p>
        </div>
    </div>
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/js/bootstrap.bundle.min.js"></script>
    <script>
        document.addEventListener('DOMContentLoaded', function() {
            const form = document.getElementById('scanForm');
            const urlInput = document.getElementById('urlInput');
            const loading = document.getElementById('loading');
            const resultContainer = document.getElementById('resultContainer');
            const resultContent = document.getElementById('resultContent');
            const deepCheck = document.getElementById('deepCheck');
            const exampleBtn = document.getElementById('exampleBtn');
            
            exampleBtn.addEventListener('click', function() {
                urlInput.value = 'https://httpbin.org/html';
            });
            
            form.addEventListener('submit', function(e) {
                e.preventDefault();
                const url = urlInput.value.trim();
                if (!url) {
                    alert('Please enter a URL');
                    return;
                }
                loading.style.display = 'block';
                resultContainer.classList.add('d-none');
                resultContent.innerHTML = '';
                
                fetch('/scan', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ url: url, deep: deepCheck.checked })
                })
                .then(response => response.json())
                .then(data => {
                    loading.style.display = 'none';
                    if (data.error) {
                        resultContent.innerHTML = '<div class="alert alert-danger">Error: ' + data.error + '</div>';
                        resultContainer.classList.remove('d-none');
                        return;
                    }
                    resultContent.innerHTML = formatResult(data);
                    resultContainer.classList.remove('d-none');
                })
                .catch(error => {
                    loading.style.display = 'none';
                    resultContent.innerHTML = '<div class="alert alert-danger">Network Error: ' + error.message + '</div>';
                    resultContainer.classList.remove('d-none');
                });
            });
            
            function formatResult(result) {
                const difficultyClass = result.assessment.difficulty === 'high' ? 'risk-high' : result.assessment.difficulty === 'medium' ? 'risk-medium' : 'risk-low';
                const badgeClass = difficultyClass === 'risk-high' ? 'danger' : difficultyClass === 'risk-medium' ? 'warning' : 'success';
                let risksHtml = '';
                if (result.assessment.key_risks && result.assessment.key_risks.length > 0) {
                    risksHtml = '<div class="mb-3"><h6><i class="mdi mdi-alert-circle me-2"></i>Key Risks:</h6><ul class="mb-0">' + result.assessment.key_risks.map(risk => '<li>' + risk + '</li>').join('') + '</ul></div>';
                } else {
                    risksHtml = '<p class="text-success"><i class="mdi mdi-check-circle me-2"></i>No significant risks detected</p>';
                }
                return '<div class="mb-3"><h5><i class="mdi mdi-link me-2"></i>Target: <a href="' + result.url + '" target="_blank">' + result.url + '</a></h5><p><small class="text-muted">Assessment Time: ' + new Date(result.timestamp).toLocaleString() + '</small></p></div><div class="mb-3"><h6><i class="mdi mdi-speedometer me-2"></i>Overall Assessment</h6><div class="d-flex justify-content-between"><span>Difficulty:</span><span class="badge bg-' + badgeClass + '">' + result.assessment.difficulty + '</span></div><div class="mt-2"><small><i class="mdi mdi-tools me-2"></i>Recommended Tool: ' + result.assessment.recommended_tool + '</small></div></div>' + risksHtml + '<div class="mb-3"><h6><i class="mdi mdi-information-outline me-2"></i>Basic Information</h6><div class="row"><div class="col-md-6"><p><i class="mdi mdi-robot me-2"></i>robots.txt: ' + (result.basic.robots_txt_exists ? 'Exists' : 'Not found') + '</p><p><i class="mdi mdi-sitemap me-2"></i>sitemap: ' + (result.basic.sitemap_urls.length > 0 ? 'Exists' : 'Not found') + '</p></div><div class="col-md-6"><p><i class="mdi mdi-rss me-2"></i>RSS/Feed: ' + (result.basic.rss_urls.length > 0 ? 'Exists' : 'Not found') + '</p><p><i class="mdi mdi-api me-2"></i>API Docs: ' + (result.basic.api_docs.length > 0 ? 'Exists' : 'Not found') + '</p></div></div></div><div class="mb-3"><h6><i class="mdi mdi-layer-measure me-2"></i>Tech Stack Detection</h6><div class="row"><div class="col-md-6"><p><i class="mdi mdi-language-html5 me-2"></i>Frontend: ' + result.tech_stack.framework + '</p><p><i class="mdi mdi-mobile-frame-measure-variant me-2"></i>Dynamic Render: ' + (result.tech_stack.dynamic_rendering ? 'Yes' : 'No') + '</p></div><div class="col-md-6"><p><i class="mdi mdi-shield-check me-2"></i>WAF/CDN: ' + result.tech_stack.cdn_waf + '</p><p><i class="mdi mdi-account-lock me-2"></i>Captcha: ' + (result.tech_stack.captcha.length > 0 ? result.tech_stack.captcha.join(', ') : 'None') + '</p></div></div></div><div class="mb-3"><h6><i class="mdi mdi-eye me-2"></i>Anti-Spider Detection</h6><div class="row"><div class="col-md-4"><p><i class="mdi mdi-account-me me-2"></i>User-Agent Check: ' + result.anti_spider.user_agent_check + '</p></div><div class="col-md-4"><p><i class="mdi mdi-speedometer me-2"></i>Rate Limit: ' + (result.anti_spider.rate_limit_triggered ? 'Triggered' : 'Not triggered') + '</p></div><div class="col-md-4"><p><i class="mdi mdi-language-javascript me-2"></i>JS Challenge: ' + (result.anti_spider.js_challenge ? 'Yes' : 'No') + '</p></div></div></div><div class="mt-4 p-3 bg-light rounded"><h6><i class="mdi mdi-file-document me-2"></i>Code Template Suggestion</h6><pre class="bg-white p-3 rounded"><code>' + result.assessment.code_template + '</code></pre></div><div class="mt-3"><h6><i class="mdi mdi-gavel me-2"></i>Compliance Note</h6><pre class="bg-white p-3 rounded">' + result.assessment.legal_note + '</pre></div>';
            }
        });
    </script>
</body>
</html>`;

export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);
    
    if (request.method === 'POST' && url.pathname === '/scan') {
      return await onRequestPost({ request, env, ctx });
    }
    
    return new Response(INDEX_HTML, {
      headers: { 'Content-Type': 'text/html' }
    });
  }
};