import html
import re

# Regex patterns for stripping non-content blocks and tags
_STYLE_SCRIPT_PATTERN = re.compile(
    r"<(script|style|head|svg|noscript)[^>]*>.*?</\1>",
    re.IGNORECASE | re.DOTALL,
)
_COMMENT_PATTERN = re.compile(r"<!--.*?-->", re.DOTALL)
_BLOCK_BREAK_PATTERN = re.compile(
    r"</?(?:p|div|tr|li|h[1-6]|blockquote|pre|hr|br|table|thead|tbody|tfoot|article|section|header|footer)[^>]*>",
    re.IGNORECASE,
)
_TAG_PATTERN = re.compile(r"<[^>]+>")
_MULTIPLE_NEWLINES_PATTERN = re.compile(r"\n{3,}")
_SPACES_PATTERN = re.compile(r"[ \t]+")


def clean_html_text(raw_text: str | None) -> str:
    """
    Converts HTML-rich or markup-tainted text into clean, readable plain text:
    1. Removes <style>, <script>, <head>, and comment blocks.
    2. Inserts line breaks for block elements (<p>, <br>, <div>, <li>, <tr>, headings).
    3. Strips all remaining HTML tags.
    4. Decodes HTML entities (&amp;, &nbsp;, &quot;, &#39;, etc.).
    5. Normalizes whitespace and line breaks.
    """
    if not raw_text:
        return ""

    if not isinstance(raw_text, str):
        try:
            raw_text = str(raw_text)
        except Exception:
            return ""

    text = raw_text.strip()
    if not text:
        return ""

    # Check if text contains any HTML tags
    if "<" in text and ">" in text:
        # 1. Remove style, script, head, svg, noscript
        text = _STYLE_SCRIPT_PATTERN.sub("", text)
        # 2. Remove comments
        text = _COMMENT_PATTERN.sub("", text)
        # 3. Replace block tags and <br> with newlines
        text = _BLOCK_BREAK_PATTERN.sub("\n", text)
        # 4. Remove all remaining inline tags
        text = _TAG_PATTERN.sub("", text)

    # 5. Decode HTML entities (&nbsp;, &amp;, &#39;, &quot;, &lt;, &gt;, etc.)
    text = html.unescape(text)
    # Replace non-breaking spaces explicitly
    text = text.replace("\xa0", " ")

    # 6. Normalize whitespace on each line
    lines = [_SPACES_PATTERN.sub(" ", line).strip() for line in text.splitlines()]

    # 7. Recombine and collapse excessive blank lines
    cleaned = "\n".join(lines)
    cleaned = _MULTIPLE_NEWLINES_PATTERN.sub("\n\n", cleaned)

    return cleaned.strip()
