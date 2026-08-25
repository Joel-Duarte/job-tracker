def normalize_job_url(url: str | None) -> str | None:
    """
    Cleans leading and trailing whitespace while preserving the exact original URL,
    including all query parameters, parameter ordering, fragments, and paths.
    """
    if not url or not isinstance(url, str):
        return None

    cleaned = url.strip()
    return cleaned if cleaned else None
