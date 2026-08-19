import html
import re


def render_markdown(text: str) -> str:
    """Standard Python Markdown to HTML renderer mirroring the frontend utility.

    Escapes raw HTML and converts basic Markdown syntax to HTML strings.
    """
    if not text or not text.strip():
        return ""

    escaped = html.escape(text)

    # 1. Fenced code blocks ```code```
    escaped = re.sub(
        r"```([\s\S]*?)```",
        lambda m: f"<pre><code>{m.group(1).strip()}</code></pre>",
        escaped,
    )

    # 2. Inline code `code`
    escaped = re.sub(r"`([^`]+)`", r"<code>\1</code>", escaped)

    # 3. Headings
    escaped = re.sub(r"^### (.*$)", r"<h3>\1</h3>", escaped, flags=re.MULTILINE)
    escaped = re.sub(r"^## (.*$)", r"<h2>\1</h2>", escaped, flags=re.MULTILINE)
    escaped = re.sub(r"^# (.*$)", r"<h1>\1</h1>", escaped, flags=re.MULTILINE)

    # 4. Bold and Italics
    escaped = re.sub(r"\*\*(.*?)\*\*", r"<strong>\1</strong>", escaped)
    escaped = re.sub(r"\*(.*?)\*", r"<em>\1</em>", escaped)

    # 5. Lists
    lines = escaped.splitlines()
    in_list = False
    out = []

    for line in lines:
        bullet_match = re.match(r"^[\-\*]\s+(.*)$", line)
        if bullet_match:
            if not in_list:
                in_list = True
                out.append('<ul class="jd-list">')
            out.append(f"<li>{bullet_match.group(1)}</li>")
        else:
            if in_list:
                in_list = False
                out.append("</ul>")
            out.append(line)

    if in_list:
        out.append("</ul>")

    res = "\n".join(out)
    res = (
        res.replace("\n", "<br>").replace("<br><ul", "<ul").replace("/ul><br>", "</ul>")
    )
    return res
