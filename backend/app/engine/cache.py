import hashlib
from datetime import datetime, timezone
from sqlalchemy import Column, DateTime, Float, Integer, JSON, String, Text, UniqueConstraint, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import Base
from app.engine.elicitor import elicit_reaction
from app.engine.simulator import get_scorer
from app.models.persona import UserProfile
from app.models.product import Product


class EvaluationCache(Base):
    __tablename__ = "evaluation_cache"
    __table_args__ = (UniqueConstraint("persona_id", "product_id", name="uq_persona_product"),)

    id = Column(Integer, primary_key=True, index=True)
    persona_id = Column(Integer, nullable=False, index=True)
    product_id = Column(Integer, nullable=False, index=True)
    content_hash = Column(String(64), nullable=False, default="")
    raw_reaction = Column(Text, nullable=False)
    ssr_probabilities = Column(JSON, nullable=False)
    base_utility_u0 = Column(Float, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


def _build_content_hash(persona: UserProfile, product: Product) -> str:
    payload = "|".join([
        str(product.name),
        f"{product.price:.2f}",
        str(product.description or ""),
        str(persona.age_group.value if hasattr(persona.age_group, "value") else persona.age_group),
        f"{persona.monthly_budget:.2f}",
        str(persona.bio or ""),
    ])
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


async def get_or_compute_evaluation(
    session: AsyncSession,
    persona: UserProfile,
    product: Product,
    force_refresh: bool = False,
) -> EvaluationCache:
    current_hash = _build_content_hash(persona, product)

    stmt = select(EvaluationCache).where(
        EvaluationCache.persona_id == persona.id,
        EvaluationCache.product_id == product.id,
    )
    cached = (await session.execute(stmt)).scalar_one_or_none()

    if cached and not force_refresh and cached.content_hash == current_hash:
        return cached

    # Cache miss, stale content hash, or forced refresh -> call Ollama + SSR scorer
    reaction = await elicit_reaction(persona, product)
    ssr = get_scorer().score_reaction(reaction)

    if cached:
        cached.content_hash = current_hash
        cached.raw_reaction = reaction
        cached.ssr_probabilities = ssr.probabilities
        cached.base_utility_u0 = ssr.base_utility_u0
        cached.updated_at = datetime.now(timezone.utc)
    else:
        cached = EvaluationCache(
            persona_id=persona.id,
            product_id=product.id,
            content_hash=current_hash,
            raw_reaction=reaction,
            ssr_probabilities=ssr.probabilities,
            base_utility_u0=ssr.base_utility_u0,
        )
        session.add(cached)

    await session.commit()
    await session.refresh(cached)
    return cached