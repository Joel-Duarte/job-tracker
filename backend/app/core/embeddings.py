import logging
from fastapi import HTTPException, status

from app.core.llm_factory import get_embeddings_model

logger = logging.getLogger(__name__)


async def generate_query_embedding(text: str) -> list[float]:
    """Generates a vector embedding for an incoming search query string using LangChain Embeddings."""
    try:
        embeddings = await get_embeddings_model()
        return await embeddings.aembed_query(text)
    except Exception as err:
        logger.error(
            "Failed to generate search query embedding: %s", err, exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to generate search query embedding: {str(err)}",
        )
