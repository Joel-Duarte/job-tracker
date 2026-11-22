from fastapi import HTTPException, status


async def generate_query_embedding(text: str) -> list[float]:
    """Reject vector query generation while embeddings are disabled."""
    raise HTTPException(
        status_code=status.HTTP_410_GONE,
        detail="Vector embeddings are disabled.",
    )
