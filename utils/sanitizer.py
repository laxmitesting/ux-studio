import re
from typing import Tuple

MIN_HTML_BYTES = 200

def extract_clean_html(raw_llm_output: str) -> str:
    text = raw_llm_output.strip()
    
    # Strip markdown code fences if present
    match = re.search(r"```(?:html)?\s*(.*?)\s*```", text, re.DOTALL | re.IGNORECASE)
    if match:
        text = match.group(1).strip()
    
    # Isolate content from opening HTML tag to closing HTML tag
    start_match = re.search(r"(<!DOCTYPE html>|<html\b[^>]*>)", text, re.IGNORECASE)
    end_match = re.search(r"</html>", text, re.IGNORECASE)
    
    if start_match and end_match:
        start_idx = start_match.start()
        end_idx = end_match.end()
        return text[start_idx:end_idx].strip()
        
    return text


def validate_html_structure(html_content: str) -> Tuple[bool, str]:
    if len(html_content.encode("utf-8")) < MIN_HTML_BYTES:
        return False, f"HTML content too small (< {MIN_HTML_BYTES} bytes)"
        
    required_tags = ["<html", "</html>", "<body", "</body>"]
    for tag in required_tags:
        if tag not in html_content.lower():
            return False, f"Missing required structural tag: {tag}"
            
    return True, "Valid"


def create_fallback_html(archetype: str, error_message: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Generation Error - {archetype.capitalize()}</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            background-color: #f8f9fa;
            color: #212529;
            display: flex;
            align-items: center;
            justify-content: center;
            height: 100vh;
            margin: 0;
        }}
        .card {{
            background: #ffffff;
            border: 1px solid #dee2e6;
            border-radius: 8px;
            padding: 32px;
            max-width: 500px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.05);
            text-align: center;
        }}
        h2 {{ color: #dc3545; margin-top: 0; }}
        code {{ background: #f1f3f5; padding: 4px 8px; border-radius: 4px; display: block; margin-top: 12px; }}
    </style>
</head>
<body>
    <div class="card">
        <h2>Generation Failed</h2>
        <p>Could not generate the <strong>{archetype}</strong> variant.</p>
        <code>{error_message}</code>
    </div>
</body>
</html>"""