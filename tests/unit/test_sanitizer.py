import pytest
from utils.sanitizer import extract_clean_html, validate_html_structure, create_fallback_html

def test_extract_clean_html_with_fences():
    raw_output = (
        "Here is the page:\n"
        "```html\n"
        "<!DOCTYPE html>\n"
        "<html>\n"
        "<head><title>Test</title></head>\n"
        "<body><h1>Hello World</h1></body>\n"
        "</html>\n"
        "```\n"
        "Hope you like it!"
    )
    clean = extract_clean_html(raw_output)
    assert clean.startswith("<!DOCTYPE html>")
    assert clean.endswith("</html>")
    assert "Here is the page:" not in clean
    assert "Hope you like it!" not in clean

def test_extract_clean_html_without_fences():
    raw_output = "<!DOCTYPE html><html><head></head><body>Content</body></html>"
    clean = extract_clean_html(raw_output)
    assert clean == raw_output

def test_validate_html_structure_valid():
    valid_html = "<!DOCTYPE html><html><head><title>Valid</title></head><body>" + ("x" * 200) + "</body></html>"
    is_valid, reason = validate_html_structure(valid_html)
    assert is_valid is True
    assert reason == "Valid"

def test_validate_html_structure_missing_tags():
    invalid_html = "<div>Only a div" + ("x" * 200) + "</div>"
    is_valid, reason = validate_html_structure(invalid_html)
    assert is_valid is False
    assert "Missing required structural tag" in reason

def test_validate_html_structure_too_short():
    short_html = "<html><body>short</body></html>"
    is_valid, reason = validate_html_structure(short_html)
    assert is_valid is False
    assert "too small" in reason

def test_create_fallback_html():
    fallback = create_fallback_html("minimalist", "API Timeout")
    assert "<!DOCTYPE html>" in fallback
    assert "minimalist" in fallback
    assert "API Timeout" in fallback