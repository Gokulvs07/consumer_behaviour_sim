from dataclasses import dataclass
from app.models.persona import UserProfile
from app.models.product import Product


@dataclass
class ScoredProduct:
    product: Product
    base_utility_u0: float


@dataclass
class OptimizationResult:
    budget_allocated: float
    total_spent: float
    remaining_budget: float
    final_basket: list[dict]
    decision_trace: list[dict]


def optimize_basket(
    persona: UserProfile,
    scored_products: list[ScoredProduct],
    budget_override: float | None = None,
) -> OptimizationResult:
    budget = budget_override if budget_override is not None else persona.monthly_budget
    remaining = float(budget)
    quantities: dict[int, int] = {sp.product.id: 0 for sp in scored_products}
    decision_trace: list[dict] = []
    step = 0

    while True:
        step += 1
        candidates = []

        for sp in scored_products:
            p = sp.product
            if p.price > remaining:
                continue

            q = quantities[p.id]
            mu = sp.base_utility_u0 / ((q + 1) ** p.satiation_alpha)
            price_factor = (p.price / 100.0) ** persona.price_sensitivity
            value_score = mu / price_factor

            candidates.append((value_score, mu, sp))

        if not candidates:
            decision_trace.append({
                "step": step,
                "action": "STOP",
                "reason": "No remaining products fit within remaining budget.",
                "remaining_budget": round(remaining, 2),
            })
            break

        # Pick candidate with highest price-adjusted marginal utility
        candidates.sort(key=lambda x: x[0], reverse=True)
        best_value, best_mu, best_sp = candidates[0]

        if best_value < persona.reservation_threshold:
            decision_trace.append({
                "step": step,
                "action": "STOP",
                "reason": (
                    f"Best option '{best_sp.product.name}' value ({best_value:.2f}) "
                    f"is below reservation threshold ({persona.reservation_threshold:.2f})."
                ),
                "remaining_budget": round(remaining, 2),
            })
            break

        # Add unit to basket
        prod = best_sp.product
        quantities[prod.id] += 1
        remaining -= prod.price

        decision_trace.append({
            "step": step,
            "action": "BUY",
            "product_id": prod.id,
            "product_name": prod.name,
            "unit_number": quantities[prod.id],
            "price": prod.price,
            "marginal_utility": round(best_mu, 2),
            "value_score": round(best_value, 2),
            "remaining_budget": round(remaining, 2),
        })

    final_basket = [
        {
            "product_id": sp.product.id,
            "product_name": sp.product.name,
            "brand": sp.product.brand,
            "unit_price": sp.product.price,
            "quantity": quantities[sp.product.id],
            "subtotal": round(sp.product.price * quantities[sp.product.id], 2),
        }
        for sp in scored_products
        if quantities[sp.product.id] > 0
    ]

    total_spent = round(budget - remaining, 2)
    return OptimizationResult(
        budget_allocated=round(budget, 2),
        total_spent=total_spent,
        remaining_budget=round(remaining, 2),
        final_basket=final_basket,
        decision_trace=decision_trace,
    )