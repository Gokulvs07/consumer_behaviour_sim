from collections import Counter
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.engine.elicitor import elicit_reaction
from app.engine.simulator import get_scorer
from app.models.persona import AgeGroup, UserProfile
from app.models.product import Product


async def run_market_analysis(
    session: AsyncSession,
    product_ids: list[int],
    age_group: AgeGroup | None = None,
) -> dict:
    # 1. Load target products
    products = (
        await session.execute(select(Product).where(Product.id.in_(product_ids)).order_by(Product.id))
    ).scalars().all()
    if len(products) < 2:
        raise ValueError("Provide at least 2 valid product_ids to compare.")

    # 2. Load target personas
    stmt = select(UserProfile).order_by(UserProfile.id)
    if age_group is not None:
        stmt = stmt.where(UserProfile.age_group == age_group)
    personas = (await session.execute(stmt)).scalars().all()
    if not personas:
        raise ValueError("No matching personas found.")

    scorer = get_scorer()
    persona_decisions = []
    win_counts: Counter[str] = Counter()

    # 3. Evaluate every persona against the competing options
    for persona in personas:
        evaluations = []

        for product in products:
            if product.price > persona.monthly_budget:
                evaluations.append({
                    "product_id": product.id,
                    "product_name": product.name,
                    "price": product.price,
                    "affordable": False,
                    "base_utility_u0": 0.0,
                    "value_score": 0.0,
                    "reaction": "Skipped — exceeds monthly budget.",
                })
                continue

            reaction = await elicit_reaction(persona, product)
            ssr = scorer.score_reaction(reaction)
            budget_share_pct = (product.price / persona.monthly_budget) * 100.0
            price_penalty = 0.4 * persona.price_sensitivity * budget_share_pct
            value_score = max(0.0, ssr.base_utility_u0 - price_penalty)

            evaluations.append({
                "product_id": product.id,
                "product_name": product.name,
                "price": product.price,
                "affordable": True,
                "base_utility_u0": ssr.base_utility_u0,
                "value_score": round(value_score, 2),
                "reaction": reaction,
            })

        # Pick the single best affordable product
        affordable_evals = [e for e in evaluations if e["affordable"]]
        affordable_evals.sort(key=lambda x: x["value_score"], reverse=True)

        if affordable_evals and affordable_evals[0]["value_score"] >= persona.reservation_threshold:
            winner = affordable_evals[0]
            chosen_name = winner["product_name"]
            reason = (
                f"Highest value score ({winner['value_score']}) within ₹{persona.monthly_budget:.0f} budget "
                f"(U0={winner['base_utility_u0']}/100)."
            )
        else:
            chosen_name = "NO_PURCHASE"
            reason = f"No affordable option met reservation threshold ({persona.reservation_threshold})."

        win_counts[chosen_name] += 1
        persona_decisions.append({
            "persona_id": persona.id,
            "persona_name": persona.name,
            "age_group": persona.age_group.value,
            "budget": persona.monthly_budget,
            "chosen_product": chosen_name,
            "decision_reason": reason,
            "comparisons": evaluations,
        })

    # 4. Aggregate market share
    total_personas = len(personas)
    market_share = {
        name: {
            "wins": count,
            "share_pct": round((count / total_personas) * 100, 1),
        }
        for name, count in win_counts.most_common()
    }

    return {
        "total_personas_evaluated": total_personas,
        "products_compared": [{"id": p.id, "name": p.name, "price": p.price} for p in products],
        "market_share": market_share,
        "persona_decisions": persona_decisions,
    }