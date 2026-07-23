from fastapi import APIRouter

router = APIRouter(prefix="/search", tags=["Search"])


@router.post("/semantic")
async def semantic_search():
    """Performs vector similarity search across email event embeddings."""
    pass


@router.get("/companies")
async def search_companies():
    """Performs fast trigram search to autocomplete or match company names."""
    pass