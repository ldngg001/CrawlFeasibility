"""Fingerprint database for WAF, framework and captcha detection"""

WAF_SIGNATURES = {
    "cloudflare": {
        "headers": ["cf-ray", "__cf_bm", "cf-cache-status"],
        "cookies": ["__cf_bm"],
        "body": ["cloudflare", "Checking your browser before accessing"],
    },
    "aliyun": {
        "headers": ["waf.aliyuncs.com", "aliyun"],
        "cookies": [],
        "body": ["waf.aliyuncs.com"],
    },
    "aws_cloudfront": {
        "headers": ["x-amz-cf-id", "x-amz-cf-pop"],
        "cookies": [],
        "body": [],
    },
    "incapsula": {
        "headers": ["incap_ses", "visid_incap"],
        "cookies": ["incap_ses", "visid_incap"],
        "body": ["Incapsula", "_Incapsula_Resource"],
    },
    "imperva": {
        "headers": ["x-cdn", "x-iinfo"],
        "cookies": ["x-cdn"],
        "body": ["Imperva"],
    },
    "akamai": {
        "headers": ["akamai-origin-hop", "akamai-x-cache"],
        "cookies": [],
        "body": [],
    },
    "sucuri": {
        "headers": ["x-sucuri", "x-sucuri-id"],
        "cookies": [],
        "body": ["Sucuri", "sucuri.net"],
    },
    "ddos-guard": {
        "headers": ["ddg-cache-status", "ddg-server"],
        "cookies": [],
        "body": ["ddos-guard"],
    },
}

FRAMEWORK_SIGNATURES = {
    "react": {
        "body": ["react", "react-dom", "data-reactroot", "__react"],
        "scripts": [".babelrc", "react.production.min.js"],
    },
    "vue": {
        "body": ["vue.js", "data-v-", "__vue__", "vue-router"],
        "scripts": ["vue.common.prod.js", "vue.runtime.esm.js"],
    },
    "angular": {
        "body": ["ng-app", "angular.js", "data-ng-"],
        "scripts": ["angular.min.js", "@angular/core"],
    },
    "nextjs": {
        "body": ["__NEXT_DATA__", "_next/static"],
        "scripts": [],
    },
    "nuxt": {
        "body": ["__NUXT__", "data-nuxt"],
        "scripts": [],
    },
    "svelte": {
        "body": ["svelte", "SVELTE"],
        "scripts": [],
    },
}

CAPTCHA_SIGNATURES = {
    "recaptcha": {
        "body": ["g-recaptcha", "google.com/recaptcha", "recaptcha/api"],
        "scripts": ["recaptcha.js", "www.google.com/recaptcha/api.js"],
    },
    "hcaptcha": {
        "body": ["hcaptcha", "hcaptcha.com", "cf-challenge"],
        "scripts": ["hcaptcha.com", "/hcaptcha.js"],
    },
    "turnstile": {
        "body": ["challenge-turnstile", "cloudflare.com/turnstile"],
        "scripts": ["/turnstile/", "turnstile.js"],
    },
    "geetest": {
        "body": ["geetest", "geetest.com"],
        "scripts": ["geetest.js", "static.geetest.com"],
    },
    "TencentCaptcha": {
        "body": ["tencent", "tcaptcha"],
        "scripts": ["tcaptcha.js", "captcha.js"],
    },
}

FINGERPRINTING_SIGNATURES = {
    "canvas": ["canvas", "CanvasRenderingContext", "toDataURL"],
    "webgl": ["WebGLRenderingContext", "webgl", "getParameter"],
    "audio": ["AudioContext", "OfflineAudioContext"],
    "fonts": ["font-family", "monospace", "sans-serif"],
}


def detect_waf(headers: dict, body: str) -> list[str]:
    """Detect WAF from headers and body content"""
    detected = []

    headers_lower = {k.lower(): v.lower() for k, v in headers.items()}
    body_lower = body.lower()

    for waf_name, signatures in WAF_SIGNATURES.items():
        matched = False

        for header in signatures.get("headers", []):
            if header in headers_lower:
                detected.append(waf_name)
                matched = True
                break

        if not matched:
            for cookie in signatures.get("cookies", []):
                if cookie in headers_lower.get("set-cookie", "").lower():
                    detected.append(waf_name)
                    break

        if not matched:
            for pattern in signatures.get("body", []):
                if pattern.lower() in body_lower:
                    detected.append(waf_name)
                    break

    return list(set(detected))


def detect_framework(body: str) -> list[str]:
    """Detect frontend framework from body content"""
    detected = []
    body_lower = body.lower()

    for framework, signatures in FRAMEWORK_SIGNATURES.items():
        for pattern in signatures.get("body", []):
            if pattern.lower() in body_lower:
                detected.append(framework)
                break

    return list(set(detected))


def detect_captcha(body: str) -> list[str]:
    """Detect captcha provider from body content"""
    detected = []
    body_lower = body.lower()

    for captcha, signatures in CAPTCHA_SIGNATURES.items():
        for pattern in signatures.get("body", []):
            if pattern.lower() in body_lower:
                detected.append(captcha)
                break

    return list(set(detected))


def detect_fingerprinting(body: str) -> bool:
    """Detect if site uses browser fingerprinting"""
    body_lower = body.lower()

    for technique, patterns in FINGERPRINTING_SIGNATURES.items():
        for pattern in patterns:
            if pattern.lower() in body_lower:
                return True

    return False
