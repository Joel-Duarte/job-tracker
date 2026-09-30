import html
import re
from html.parser import HTMLParser

_MULTIPLE_NEWLINES_PATTERN = re.compile(r"\n{3,}")
_SPACES_PATTERN = re.compile(r"[ \t]+")
_SKIP_TAGS = {"script", "style", "head", "svg", "noscript"}
_BREAK_TAGS = {
    "p",
    "div",
    "tr",
    "li",
    "blockquote",
    "pre",
    "hr",
    "br",
    "table",
    "thead",
    "tbody",
    "tfoot",
    "article",
    "section",
    "header",
    "footer",
    *(f"h{level}" for level in range(1, 7)),
}


class _PlainTextParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.skipped: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if self.skipped:
            if tag in _SKIP_TAGS:
                self.skipped.append(tag)
            return
        if tag in _SKIP_TAGS:
            self.skipped.append(tag)
        elif tag in _BREAK_TAGS:
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if self.skipped:
            if tag == self.skipped[-1]:
                self.skipped.pop()
            return
        if tag in _BREAK_TAGS:
            self.parts.append("\n")

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if not self.skipped and tag in _BREAK_TAGS:
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        if not self.skipped:
            self.parts.append(data)


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
        parser = _PlainTextParser()
        parser.feed(text)
        parser.close()
        text = "".join(parser.parts)

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
