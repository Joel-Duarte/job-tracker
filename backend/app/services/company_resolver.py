import difflib
import logging
import re

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.applications import CompanyModel
from app.services.domain_resolver import (
    clean_company_name,
    clean_domain,
    is_ats_vendor_match,
    is_domain_match_for_company,
)

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


def _company_tokens(name: str) -> list[str]:
    return [t for t in re.split(r"[^a-z0-9]+", name.lower()) if t]


def _is_token_subset_match(a: str, b: str) -> bool:
    """True when one cleaned name's tokens are a whole-token subset of the other's
    (e.g. 'hays' vs 'hays uk' or 'hays specialist recruitment'), guarding short acronyms.
    """
    ta = _company_tokens(a)
    tb = _company_tokens(b)
    if not ta or not tb:
        return False
    shorter, longer = (ta, tb) if len(ta) <= len(tb) else (tb, ta)
    if len("".join(shorter)) < 4:
        return False
    return set(shorter).issubset(set(longer))


async def resolve_or_create_company(
    db: AsyncSession,
    company_name: str,
    domain: str | None = None,
) -> tuple[CompanyModel, bool]:
    """
    Resolves an employer entity using multi-tier resolution:
    1. Exact normalized name match (after stripping legal/portal suffixes).
    2. Domain match (exact canonical domain or shared domain root + name alignment).
    3. Trigram fuzzy name similarity (>= 0.85) or whole-token subset match.
    4. If no match, creates and flushes a new CompanyModel.

    Returns: (CompanyModel, was_created: bool)
    """
    raw_clean = company_name.strip()
    cleaned_display = clean_company_name(raw_clean) or raw_clean
    norm_name = cleaned_display.lower()

    clean_dom = clean_domain(domain) if domain else None
    if clean_dom and any(h in clean_dom for h in GENERIC_ATS_HOSTS):
        if not is_ats_vendor_match(cleaned_display, clean_dom):
            clean_dom = None

    # Tier 1: Exact normalized name match (after stripping legal/portal suffixes)
    name_candidates = list({norm_name, raw_clean.lower()})
    stmt_name = (
        select(CompanyModel)
        .where(CompanyModel.name_normalized.in_(name_candidates))
        .limit(1)
    )
    res_name = await db.execute(stmt_name)
    company = res_name.scalar_one_or_none()
    if company:
        if clean_dom and not company.domain:
            company.domain = clean_dom
            await db.flush()
        return company, False

    # Tier 2: Canonical domain match (exact, or shared domain root + name alignment)
    if clean_dom:
        dom_root = clean_dom.split(".")[0]
        if dom_root and len(dom_root) >= 3:
            domain_filter = or_(
                CompanyModel.domain == clean_dom,
                CompanyModel.domain.ilike(f"{dom_root}.%"),
            )
        else:
            domain_filter = CompanyModel.domain == clean_dom
        stmt_domain = select(CompanyModel).where(domain_filter).limit(1)
        res_domain = await db.execute(stmt_domain)
        company = res_domain.scalar_one_or_none()
        if company and (
            company.domain == clean_dom
            or is_domain_match_for_company(company.domain, cleaned_display)
        ):
            return company, False

    # Tier 3: Trigram similarity match (>= 0.85) or whole-token subset match
    try:
        trgm_sim = func.similarity(CompanyModel.name_normalized, norm_name)
        word_sim_fwd = func.word_similarity(norm_name, CompanyModel.name_normalized)
        word_sim_rev = func.word_similarity(CompanyModel.name_normalized, norm_name)
        stmt_trgm = (
            select(
                CompanyModel,
                trgm_sim.label("sim"),
            )
            .where(
                or_(
                    trgm_sim >= 0.85,
                    word_sim_fwd >= 0.85,
                    word_sim_rev >= 0.85,
                )
            )
            .order_by(trgm_sim.desc())
            .limit(1)
        )
        res_trgm = await db.execute(stmt_trgm)
        row = res_trgm.first()
        if row:
            candidate = row[0]
            c_clean = clean_company_name(candidate.name).lower()
            sim_val = (
                row[1] if len(row) > 1 and isinstance(row[1], (int, float)) else 1.0
            )
            if sim_val >= 0.85 or _is_token_subset_match(c_clean, norm_name):
                if clean_dom and not candidate.domain:
                    candidate.domain = clean_dom
                    await db.flush()
                return candidate, False
    except Exception as err:
        # Fallback for environments where pg_trgm similarity is unavailable or mocked
        logger.debug("Trigram query fallback due to: %s", err)
        all_companies_stmt = select(CompanyModel)
        all_res = await db.execute(all_companies_stmt)
        for c in all_res.scalars().all():
            c_clean = clean_company_name(c.name).lower()
            ratio = max(
                difflib.SequenceMatcher(None, c.name_normalized, norm_name).ratio(),
                difflib.SequenceMatcher(None, c_clean, norm_name).ratio(),
            )
            if ratio >= 0.85 or _is_token_subset_match(c_clean, norm_name):
                if clean_dom and not c.domain:
                    c.domain = clean_dom
                    await db.flush()
                return c, False

    # Tier 4: Create new company record
    company = CompanyModel(
        name=raw_clean,
        name_normalized=raw_clean.lower(),
        domain=clean_dom,
    )
    db.add(company)
    await db.flush()
    return company, True
