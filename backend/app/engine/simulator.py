from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.engine.elicitor import elicit_reaction
from app.engine.optimizer import ScoredProduct, optimize_basket
from app.engine.ssr_scorer import SSRScorer
from app.models.persona import UserProfile
from app.models.product import Product
from app.models.simulation import ProductEvaluation, SimulationRun

_scorer: SSRScorer | None = None


def get_scorer() -> SSRScorer:
    global _scorer
    if _scorer is None:
        _scorer = SSRScorer()
    return _scorer


async def run_persona_simulation(
    session: AsyncSession,
    persona_id: int,
    budget_override: float | None = None,
) -> SimulationRun:
    persona = await session.get(UserProfile, persona_id)
    if not persona:
        raise ValueError(f"Persona {persona_id} not found.")

    products = (await session.execute(select(Product).order_by(Product.id))).scalars().all()
    if not products:
        raise ValueError("No products found in catalog.")

    scorer = get_scorer()
    scored_products: list[ScoredProduct] = []
    pending_evaluations: list[ProductEvaluation] = []

    # 1. Phase 2: Elicit & Score every product in the catalog
    for product in products:
        reaction = await elicit_reaction(persona, product)
        ssr = scorer.score_reaction(reaction)

        scored_products.append(ScoredProduct(product=product, base_utility_u0=ssr.base_utility_u0))
        pending_evaluations.append(
            ProductEvaluation(
                product_id=product.id,
                raw_reaction=reaction,
                reaction_embedding=ssr.embedding,
                ssr_probabilities=ssr.probabilities,
                base_utility_u0=ssr.base_utility_u0,
            )
        )

    # 2. Phase 3: Run Marginal Utility Basket Optimization
    opt = optimize_basket(persona, scored_products, budget_override=budget_override)

    # 3. Persist SimulationRun + ProductEvaluations to PostgreSQL
    sim_run = SimulationRun(
        persona_id=persona.id,
        budget_allocated=opt.budget_allocated,
        total_spent=opt.total_spent,
        remaining_budget=opt.remaining_budget,
        final_basket=opt.final_basket,
        decision_trace=opt.decision_trace,
    )
    session.add(sim_run)
    await session.flush()  # Assigns sim_run.id before linking evaluations

    for ev in pending_evaluations:
        ev.run_id = sim_run.id
        session.add(ev)

    await session.commit()
    await session.refresh(sim_run)
    return sim_run