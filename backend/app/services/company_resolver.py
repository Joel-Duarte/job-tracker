import difflib
import logging

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.applications import CompanyModel

logger = logging.getLogger(__name__)

GENERIC_ATS_HOSTS = (
    "greenhouse.io",
    "lever.co",
    "workday.com",
    "ashbyhq.com",
    "smartrecruiters.com",
    "icims.com",
    "bamboohr.com",
    "myworkdayjobs.com",
)


async def resolve_or_create_company(
    db: AsyncSession,
    company_name: str,
    domain: str | None = None,
) -> tuple[CompanyModel, bool]:
    """
    Resolves an employer entity using multi-tier resolution:
    1. Exact normalized name match.
    2. Domain match (if canonical non-ATS domain provided).
    3. Trigram fuzzy name similarity (> 0.85).
    4. If no match, creates and flushes a new CompanyModel.

    Returns: (CompanyModel, was_created: bool)
    """
    clean_name = company_name.strip()
    norm_name = clean_name.lower()
    clean_domain = domain.strip().lower() if domain else None
    if clean_domain and any(h in clean_domain for h in GENERIC_ATS_HOSTS):
        clean_domain = None

    # Tier 1: Exact normalized name match
    stmt_name = select(CompanyModel).where(CompanyModel.name_normalized == norm_name)
    res_name = await db.execute(stmt_name)
    company = res_name.scalar_one_or_none()
    if company:
        if clean_domain and not company.domain:
            company.domain = clean_domain
            await db.flush()
        return company, False

    # Tier 2: Canonical domain match
    if clean_domain:
        stmt_domain = select(CompanyModel).where(CompanyModel.domain == clean_domain)
        res_domain = await db.execute(stmt_domain)
        company = res_domain.scalar_one_or_none()
        if company:
            return company, False

    # Tier 3: Trigram similarity match (> 0.85)
    try:
        stmt_trgm = (
            select(
                CompanyModel,
                func.similarity(CompanyModel.name_normalized, norm_name).label("sim"),
            )
            .where(func.similarity(CompanyModel.name_normalized, norm_name) >= 0.85)
            .order_by(func.similarity(CompanyModel.name_normalized, norm_name).desc())
            .limit(1)
        )
        res_trgm = await db.execute(stmt_trgm)
        row = res_trgm.first()
        if row:
            company = row[0]
            if clean_domain and not company.domain:
                company.domain = clean_domain
                await db.flush()
            return company, False
    except Exception as err:
        # Fallback for environments where pg_trgm similarity is unavailable or mocked
        logger.debug("Trigram query fallback due to: %s", err)
        all_companies_stmt = select(CompanyModel)
        all_res = await db.execute(all_companies_stmt)
        for c in all_res.scalars().all():
            ratio = difflib.SequenceMatcher(None, c.name_normalized, norm_name).ratio()
            if ratio >= 0.85:
                if clean_domain and not c.domain:
                    c.domain = clean_domain
                    await db.flush()
                return c, False

    # Tier 4: Create new company record
    company = CompanyModel(
        name=clean_name,
        name_normalized=norm_name,
        domain=clean_domain,
    )
    db.add(company)
    await db.flush()
    return company, True
