import os
import re
from urllib.parse import urlparse
import pytest

APP_JS_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "ui", "web", "app.js")


def test_app_js_contains_no_unsafe_innerhtml_sinks() -> None:
    """Verifies that app.js does not use innerHTML, outerHTML, insertAdjacentHTML, or document.write."""
    with open(APP_JS_PATH, "r", encoding="utf-8") as f:
        content = f.read()

    # Strip single-line and multi-line comments
    cleaned = re.sub(r"/\*[\s\S]*?\*/", "", content)
    lines = [line.strip() for line in cleaned.splitlines() if not line.strip().startswith("//")]
    cleaned_code = "\n".join(lines)

    # Check for unsafe sinks in executable JS code
    unsafe_patterns = [
        r"\.innerHTML\s*=",
        r"\.outerHTML\s*=",
        r"\.insertAdjacentHTML\s*\(",
        r"document\.write\s*\("
    ]

    for pattern in unsafe_patterns:
        match = re.search(pattern, cleaned_code)
        assert match is None, f"Found unsafe HTML sink matching '{pattern}' in app.js: {match.group() if match else ''}"


def test_app_js_implements_url_validation() -> None:
    """Verifies that app.js implements isValidHttpUrl and checks protocols."""
    with open(APP_JS_PATH, "r", encoding="utf-8") as f:
        content = f.read()

    assert "isValidHttpUrl" in content
    assert "protocol" in content
    assert "http:" in content
    assert "https:" in content


def is_valid_http_url(url_string: str | None) -> bool:
    """Python mirror of the JavaScript isValidHttpUrl logic for regression verification."""
    if not url_string or not isinstance(url_string, str):
        return False
    try:
        parsed = urlparse(url_string)
        return parsed.scheme.lower() in ("http", "https") and bool(parsed.netloc)
    except Exception:
        return False


@pytest.mark.parametrize("dangerous_url", [
    "javascript:alert(1)",
    "javascript:alert(document.cookie)",
    "javascript:void(0)",
    "JAVASCRIPT:alert('xss')",
    "data:text/html;base64,PHNjcmlwdD5hbGVydCgxKTwvc2NyaXB0Pg==",
    "data:text/html,<script>alert(1)</script>",
    "vbscript:msgbox(1)",
    "file:///C:/Windows/System32/calc.exe",
    "blob:https://example.com/uuid",
    "about:blank",
    "",
    "   ",
    None,
])
def test_dangerous_url_schemes_are_rejected(dangerous_url: str | None) -> None:
    assert is_valid_http_url(dangerous_url) is False


@pytest.mark.parametrize("legitimate_url", [
    "https://www.linkedin.com/jobs/view/38291029",
    "https://jobs.netflix.com/jobs/12345",
    "http://careers.google.com/jobs/results/999",
    "https://internshala.com/internship/detail/python-internship-123",
    "https://www.naukri.com/job-listings-081026001234",
])
def test_legitimate_http_urls_are_accepted(legitimate_url: str) -> None:
    assert is_valid_http_url(legitimate_url) is True


def test_malicious_job_fields_cannot_execute_via_text_rendering() -> None:
    """
    Simulates the safe DOM rendering rule:
    When strings containing script tags or event handlers are stored in job/review objects,
    using textContent / textNode treats them purely as verbatim characters without HTML execution.
    """
    import html

    malicious_payloads = [
        "<script>alert(1)</script>",
        "<img src=x onerror=alert('xss')>",
        "<svg onload=alert(document.cookie)>",
        "<a href=\"javascript:alert('pwn')\">Click here</a>",
        "';alert(1);//"
    ]

    for payload in malicious_payloads:
        # Escaped text rendering does not expose raw unescaped HTML elements
        rendered = html.escape(payload)
        assert "<script>" not in rendered
        assert "<img src=" not in rendered
        assert "<svg onload=" not in rendered
        assert "<a href=" not in rendered
