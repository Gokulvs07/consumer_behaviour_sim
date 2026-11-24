from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.engine.cache import get_or_compute_evaluation
from app.models.persona import AgeGroup, UserProfile
from app.models.product import Product
import math


LOSS_AVERSION = 2.0
def _compute_value_score(
    u0: float,
    price: float,
    persona: UserProfile,
    ref_price: float | None = None,
    loss_aversion: float = LOSS_AVERSION,
) -> float:
    anchor = max(ref_price if ref_price is not None else persona.monthly_budget, 1.0)
    rel = price / anchor
    effective_rel = rel if rel <= 1.0 else 1.0 + loss_aversion * (rel - 1.0)
    price_penalty = 25.0 * persona.price_sensitivity * effective_rel
    return max(0.0, u0 - price_penalty)


def _compute_wtp(u0: float, persona: UserProfile) -> float:
    """Max price where Net Utility == reservation_threshold, capped at monthly_budget."""
    if u0 <= persona.reservation_threshold or persona.price_sensitivity <= 0:
        return 0.0
    raw_wtp = ((u0 - persona.reservation_threshold) / (40.0 * persona.price_sensitivity)) * persona.monthly_budget
    return round(min(max(raw_wtp, 0.0), persona.monthly_budget), 2)

def _compute_switching_price(
    u0: float,
    benchmark_val: float,
    persona: UserProfile,
    ref_price: float,
    loss_aversion: float = LOSS_AVERSION,
) -> float:
    """Exact inverse of _compute_value_score with asymmetric loss aversion."""
    if u0 <= benchmark_val or persona.price_sensitivity <= 0:
        return 0.0
    anchor = max(ref_price, 1.0)
    effective_rel = (u0 - benchmark_val) / (25.0 * persona.price_sensitivity)
    rel = (
        effective_rel
        if effective_rel <= 1.0
        else 1.0 + (effective_rel - 1.0) / loss_aversion
    )
    raw_switch = rel * anchor
    return round(min(max(raw_switch, 0.0), persona.monthly_budget), 2)

async def run_price_sweep(
    session: AsyncSession,
    target_product_id: int,
    competitor_ids: list[int],
    min_pct: float = -30.0,
    max_pct: float = 30.0,
    steps: int = 7,
    age_group: AgeGroup | None = None,
    force_refresh: bool = False,
    choice_model: str = "deterministic",
    temperature: float = 5.0,
) -> dict:
    all_ids = list(dict.fromkeys([target_product_id, *competitor_ids]))
    if len(all_ids) < 2:
        raise ValueError("Provide a target_product_id and at least 1 competitor_id.")

    products = (
        await session.execute(select(Product).where(Product.id.in_(all_ids)))
    ).scalars().all()
    product_map = {p.id: p for p in products}

    if target_product_id not in product_map:
        raise ValueError(f"Target product {target_product_id} not found.")

    target = product_map[target_product_id]
    competitors = [product_map[pid] for pid in competitor_ids if pid in product_map and pid != target_product_id]
    all_shelf_products = [target, *competitors]
    ref_price = sum(p.price for p in all_shelf_products) / len(all_shelf_products)
    stmt = select(UserProfile).order_by(UserProfile.id)
    if age_group is not None:
        stmt = stmt.where(UserProfile.age_group == age_group)
    personas = (await session.execute(stmt)).scalars().all()
    if not personas:
        raise ValueError("No matching personas found.")

    # 1. Fetch or compute cached U0 for every (persona, product) pair
    u0_matrix: dict[tuple[int, int], float] = {}
    for persona in personas:
        for prod in [target, *competitors]:
            ev = await get_or_compute_evaluation(session, persona, prod, force_refresh=force_refresh)
            u0_matrix[(persona.id, prod.id)] = ev.base_utility_u0

    # 2. Generate price points (always include current catalog price)
    steps = max(steps, 2)
    step_size = (max_pct - min_pct) / (steps - 1)
    pct_points = [round(min_pct + i * step_size, 1) for i in range(steps)]
    if 0.0 not in pct_points:
        pct_points.append(0.0)
        pct_points.sort()

    # 3. Run zero-LLM discrete choice sweep across every price point
    total_personas = len(personas)
    sweep_curve = []
    base_wins = 0

    for pct in pct_points:
        test_price = round(max(1.0, target.price * (1.0 + pct / 100.0)), 2)
        target_wins = 0
        competitor_wins = {c.name: 0 for c in competitors}
        no_purchase = 0

        for persona in personas:
            options = []
            if test_price <= persona.monthly_budget:
                t_u0 = u0_matrix[(persona.id, target.id)]
                t_val = _compute_value_score(t_u0, test_price, persona, ref_price)
                options.append((t_val, t_u0, -test_price, target.name))

            for comp in competitors:
                if comp.price <= persona.monthly_budget:
                    c_u0 = u0_matrix[(persona.id, comp.id)]
                    c_val = _compute_value_score(c_u0, comp.price, persona, ref_price)
                    options.append((c_val, c_u0, -comp.price, comp.name))

            if choice_model == "logit":
                # Include outside option (no purchase) at reservation_threshold
                scored = [(opt[3], opt[0]) for opt in options] + [
                    ("__no_purchase__", persona.reservation_threshold)
                ]
                max_v = max(v for _, v in scored)
                tau = max(temperature, 0.1)
                weights = [math.exp((v - max_v) / tau) for _, v in scored]
                total_w = sum(weights)

                for (name, _), w in zip(scored, weights):
                    prob = w / total_w
                    if name == target.name:
                        target_wins += prob
                    elif name == "__no_purchase__":
                        no_purchase += prob
                    else:
                        competitor_wins[name] += prob
            else:
                options.sort(reverse=True)
                if options and options[0][0] >= persona.reservation_threshold:
                    winner_name = options[0][3]
                    if winner_name == target.name:
                        target_wins += 1
                    else:
                        competitor_wins[winner_name] += 1
                else:
                    no_purchase += 1

        if pct == 0.0:
            base_wins = target_wins

        sweep_curve.append({
            "price_change_pct": pct,
            "test_price": test_price,
            "target_wins": round(target_wins, 2),
            "market_share_pct": round((target_wins / total_personas) * 100.0, 1),
            "projected_revenue": round(target_wins * test_price, 2),
            "competitor_wins": {k: round(v, 2) for k, v in competitor_wins.items()},
            "no_purchase_count": round(no_purchase, 2),
        })

    # 4. Compute Price Elasticity vs Base Price (PED = %ΔQ / %ΔP)
    for point in sweep_curve:
        pct_p = point["price_change_pct"]
        if pct_p != 0.0 and base_wins > 0:
            pct_q = ((point["target_wins"] - base_wins) / base_wins) * 100.0
            point["elasticity_vs_base"] = round(pct_q / pct_p, 2)
        else:
            point["elasticity_vs_base"] = None

    # 5. Optimal revenue price & persona WTP breakdown
    # 5. Optimal revenue price & competitive switching price breakdown
    optimal_point = max(sweep_curve, key=lambda x: (x["projected_revenue"], x["target_wins"]))
    wtp_breakdown = []
    for persona in personas:
        u0 = u0_matrix[(persona.id, target.id)]

        # Find best affordable competitor's net value score
        best_comp_name = "None"
        benchmark_val = persona.reservation_threshold
        for comp in competitors:
            if comp.price <= persona.monthly_budget:
                c_u0 = u0_matrix[(persona.id, comp.id)]
                c_val = _compute_value_score(c_u0, comp.price, persona, ref_price)
                if c_val > benchmark_val:
                    benchmark_val = c_val
                    best_comp_name = comp.name

        switching_price = _compute_switching_price(u0, benchmark_val, persona, ref_price)
        wtp_breakdown.append({
            "persona_name": persona.name,
            "age_group": persona.age_group.value,
            "budget": persona.monthly_budget,
            "base_utility_u0": round(u0, 2),
            "best_competitor": best_comp_name,
            "switching_price": switching_price,
            "price_headroom": round(switching_price - target.price, 2),
        })

    return {
        "target_product": {"id": target.id, "name": target.name, "base_price": target.price},
        "competitors": [{"id": c.id, "name": c.name, "price": c.price} for c in competitors],
        "total_personas": total_personas,
        "optimal_price_point": optimal_point,
        "sweep_curve": sweep_curve,
        "wtp_breakdown": wtp_breakdown,
    }