import re

# Pre-compiled Regex patterns for high-speed local PII sanitization
EMAIL_PATTERN = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b")

PHONE_PATTERN = re.compile(
    r"(?:\+?\d{1,3}[-.\s]?)?(?:\(?\d{2,4}\)?[-.\s]?)?\d{3,4}[-.\s]?\d{3,9}\b"
)

URL_PATTERN = re.compile(
    r"https?://(?:www\.)?(?:linkedin\.com/(?:in|pub)/[a-zA-Z0-9_%-]+|github\.com/[a-zA-Z0-9_%-]+|twitter\.com/[a-zA-Z0-9_%-]+|x\.com/[a-zA-Z0-9_%-]+|[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}/[^\s]*)"
)

# Address pattern: Number + street name + street type + optional city/state/zip
ADDRESS_PATTERN = re.compile(
    r"\b\d{1,5}\s+[A-Za-z0-9\.\s]{2,30}\s+(?:Street|St|Avenue|Ave|Boulevard|Blvd|Road|Rd|Way|Drive|Dr|Lane|Ln|Court|Ct|Circle|Cir|Terrace|Terr|Ter|Place|Pl|Square|Sq|Highway|Hwy|Parkway|Pkwy)\b(?:[,\s]+[A-Za-z\s]+[,\s]+[A-Z]{2}\s+\d{5}(?:-\d{4})?)?",
    re.IGNORECASE,
)

ADDRESS_LINE_PREFIX_PATTERN = re.compile(
    r"^(?:Address|Location|Residential Address)\s*:\s*(.+)$",
    re.IGNORECASE | re.MULTILINE,
)


def programmatic_scrub_cv(raw_text: str) -> tuple[str, dict[str, int]]:
    """
    Programmatically sanitizes direct PII (emails, phone numbers, profile URLs, physical addresses)
    locally using regular expressions before any text is dispatched to external LLM models.

    Returns:
        - scrubbed_text: str with [Email Redacted], [Phone Redacted], etc.
        - stats: dict counting redacted items per category
    """
    if not raw_text or not raw_text.strip():
        return raw_text, {
            "emails": 0,
            "phones": 0,
            "urls": 0,
            "addresses": 0,
            "header_name": 0,
        }

    stats = {"emails": 0, "phones": 0, "urls": 0, "addresses": 0, "header_name": 0}
    lines = raw_text.splitlines()

    # 1. First line candidate name heuristic (if short and not a section heading)
    excluded_headings = {
        "summary",
        "profile",
        "objective",
        "experience",
        "education",
        "skills",
        "projects",
        "work history",
        "technical skills",
        "certifications",
        "about me",
        "curriculum vitae",
        "resume",
    }

    if lines:
        first_line_idx = 0
        while first_line_idx < len(lines) and not lines[first_line_idx].strip():
            first_line_idx += 1

        if first_line_idx < len(lines):
            first_line = lines[first_line_idx].strip()
            first_line_lower = first_line.lower()
            if (
                len(first_line) <= 45
                and first_line_lower not in excluded_headings
                and not any(first_line_lower.startswith(h) for h in excluded_headings)
                and not any(
                    char in first_line for char in [":", ";", "{", "}", "#", "/"]
                )
            ):
                lines[first_line_idx] = "[Candidate Name]"
                stats["header_name"] += 1

    text = "\n".join(lines)

    # 2. Explicit Address: ... line prefix replacement
    def _replace_address_line(match: re.Match) -> str:
        stats["addresses"] += 1
        return "Address: [Address Redacted]"

    text = ADDRESS_LINE_PREFIX_PATTERN.sub(_replace_address_line, text)

    # 3. Email Scrubbing
    emails_found = EMAIL_PATTERN.findall(text)
    stats["emails"] = len(emails_found)
    text = EMAIL_PATTERN.sub("[Email Redacted]", text)

    # 4. URL & Social Profile Scrubbing
    urls_found = URL_PATTERN.findall(text)
    stats["urls"] = len(urls_found)
    text = URL_PATTERN.sub("[Profile Link Redacted]", text)

    # 5. Street Address Pattern Scrubbing
    addresses_found = ADDRESS_PATTERN.findall(text)
    stats["addresses"] += len(addresses_found)
    text = ADDRESS_PATTERN.sub("[Address Redacted]", text)

    # 6. Phone Number Scrubbing (applied after URLs to prevent false positives)
    def _replace_phone(match: re.Match) -> str:
        val = match.group(0).strip()
        # Ensure it contains at least 7 digits to avoid matching small numbers/years
        digit_count = sum(c.isdigit() for c in val)
        if 7 <= digit_count <= 15:
            stats["phones"] += 1
            return "[Phone Redacted]"
        return val

    text = PHONE_PATTERN.sub(_replace_phone, text)

    return text, stats
