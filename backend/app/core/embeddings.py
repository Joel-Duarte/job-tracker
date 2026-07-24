from typing import List
import httpx
from fastapi import HTTPException, status
from app.core.config import settings


async def generate_query_embedding(text: str) -> List[float]:
    """Generates a vector embedding for an incoming search query string."""
    if not settings.EMBEDDING_API_URL:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Embedding API URL is not configured in settings.",
        )

    headers = {"Content-Type": "application/json"}
    if settings.EMBEDDING_API_KEY:
        headers["Authorization"] = f"Bearer {settings.EMBEDDING_API_KEY}"

    payload = {
        "model": settings.EMBEDDING_MODEL_NAME,
        "input": text,
    }

    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            response = await client.post(settings.EMBEDDING_API_URL, json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()
            
            # OpenAI / Standard embedding API response format
            return data["data"][0]["embedding"]
        except Exception as err:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Failed to generate search query embedding: {str(err)}",
            )