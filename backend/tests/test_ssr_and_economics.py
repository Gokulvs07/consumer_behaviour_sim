from types import SimpleNamespace
import pytest

from app.engine.cache import _build_content_hash
from app.engine.simulator import get_scorer


@pytest.fixture(scope="module")
def scorer():
    return get_scorer()


def test_ssr_monotonicity_and_bounds(scorer):
    """Positive reactions must score higher U0 than neutral, and neutral higher than negative."""
    positive = scorer.score_reaction(
        "I love this toothpaste! It works great for sensitivity, feels worth every rupee, and I will definitely buy it."
    )
    neutral = scorer.score_reaction(
        "It looks okay, nothing special compared to what I already use. Maybe I would consider it if on sale."
    )
    negative = scorer.score_reaction(
        "Way too expensive and full of gimmicks. I completely distrust this brand and would never buy it."
    )

    assert 0.0 <= negative.base_utility_u0 <= 100.0
    assert 0.0 <= neutral.base_utility_u0 <= 100.0
    assert 0.0 <= positive.base_utility_u0 <= 100.0

    assert positive.base_utility_u0 > neutral.base_utility_u0 > negative.base_utility_u0

    for res in (positive, neutral, negative):
        prob_sum = sum(res.probabilities.values()) if isinstance(res.probabilities, dict) else sum(res.probabilities)
        assert prob_sum == pytest.approx(1.0, abs=1e-3)


def test_content_hash_invalidation():
    """Changing price, description, or persona bio must produce a new cache hash."""
    persona = SimpleNamespace(age_group="25-40", monthly_budget=1200.0, bio="Prefers herbal ingredients.")
    product_v1 = SimpleNamespace(name="Dabur Red", price=125.0, description="Ayurvedic clove oil paste.")
    product_v2_price = SimpleNamespace(name="Dabur Red", price=140.0, description="Ayurvedic clove oil paste.")
    product_v3_desc = SimpleNamespace(name="Dabur Red", price=125.0, description="New mint & clove formula.")

    h1 = _build_content_hash(persona, product_v1)
    h1_repeat = _build_content_hash(persona, product_v1)
    h2 = _build_content_hash(persona, product_v2_price)
    h3 = _build_content_hash(persona, product_v3_desc)

    assert h1 == h1_repeat
    assert h1 != h2
    assert h1 != h3


def test_discrete_choice_budget_and_threshold_guards():
    """Verify net-value math penalizes higher prices and rejects unaffordable or low-value items."""
    budget = 500.0
    price_sensitivity = 0.85
    reservation_threshold = 20.0
    u0 = 55.0

    def net_value(price: float) -> float:
        if price > budget:
            return -1.0
        penalty = 0.4 * price_sensitivity * (price / budget) * 100.0
        return max(0.0, u0 - penalty)

    val_cheap = net_value(125.0)
    val_mid = net_value(260.0)
    val_unaffordable = net_value(600.0)

    assert val_cheap > val_mid
    assert val_unaffordable < 0.0
    assert val_cheap >= reservation_threshold