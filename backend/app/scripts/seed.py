import asyncio
from sqlalchemy import text
from app.core.database import AsyncSessionLocal, Base, engine
from app.models.persona import AgeGroup, UserProfile
from app.models.product import Product
from app.models.simulation import ProductEvaluation, SimulationRun  # noqa: F401


SEED_PERSONAS = [
    UserProfile(
        name="Aarav",
        age=21,
        age_group=AgeGroup.GEN_Z,
        occupation="College Student",
        monthly_budget=500.0,
        price_sensitivity=1.35,
        reservation_threshold=18.0,
        bio="Lives in a hostel, cares about aesthetics and teeth whitening, switches brands for discounts.",
        traits={"brand_loyalty": "low", "priorities": ["whitening", "freshness", "low_price"]},
    ),
    UserProfile(
        name="Priya",
        age=31,
        age_group=AgeGroup.MILLENNIAL,
        occupation="Product Designer",
        monthly_budget=1200.0,
        price_sensitivity=1.0,
        reservation_threshold=12.0,
        bio="Reads ingredient labels, prefers herbal or clean formulations, willing to pay extra for quality.",
        traits={"brand_loyalty": "medium", "priorities": ["natural_ingredients", "sustainability"]},
    ),
    UserProfile(
        name="Rajesh",
        age=48,
        age_group=AgeGroup.GEN_X,
        occupation="Operations Manager",
        monthly_budget=1500.0,
        price_sensitivity=0.85,
        reservation_threshold=10.0,
        bio="Shops for a family of four, trusts clinical/dentist-recommended brands, prefers value packs.",
        traits={"brand_loyalty": "high", "priorities": ["family_value", "cavity_protection"]},
    ),
    UserProfile(
        name="Meenakshi",
        age=64,
        age_group=AgeGroup.SENIOR,
        occupation="Retired Teacher",
        monthly_budget=800.0,
        price_sensitivity=1.15,
        reservation_threshold=14.0,
        bio="Deals with tooth sensitivity and gum discomfort, avoids flashy gimmicks, sticks to trusted brands.",
        traits={"brand_loyalty": "very_high", "priorities": ["sensitivity_relief", "gum_care"]},
    ),
]

SEED_PRODUCTS = [
    Product(
        name="Colgate Visible White O2",
        brand="Colgate",
        category="toothpaste",
        price=260.0,
        satiation_alpha=1.6,
        description="Active oxygen whitening toothpaste promising visibly whiter teeth in 3 days.",
        attributes={"benefit": "whitening", "size_g": 100},
    ),
    Product(
        name="Colgate Strong Teeth Family Pack",
        brand="Colgate",
        category="toothpaste",
        price=195.0,
        satiation_alpha=1.5,
        description="Calcium-boost anti-cavity toothpaste in a 300g family saver pack.",
        attributes={"benefit": "cavity_protection", "size_g": 300},
    ),
    Product(
        name="Sensodyne Repair & Protect",
        brand="Sensodyne",
        category="toothpaste",
        price=240.0,
        satiation_alpha=1.6,
        description="Clinically proven NovaMin formula for deep sensitivity repair and gum protection.",
        attributes={"benefit": "sensitivity", "size_g": 100},
    ),
    Product(
        name="Dabur Red Herbal Paste",
        brand="Dabur",
        category="toothpaste",
        price=125.0,
        satiation_alpha=1.5,
        description="Ayurvedic formulation with clove oil, pudina, and tomar for natural oral care.",
        attributes={"benefit": "herbal", "size_g": 200},
    ),
    Product(
        name="Colgate Plax Peppermint Mouthwash",
        brand="Colgate",
        category="mouthwash",
        price=180.0,
        satiation_alpha=1.2,
        description="Alcohol-free antibacterial mouthwash for 24/7 fresh breath protection.",
        attributes={"benefit": "fresh_breath", "size_ml": 250},
    ),
]


async def seed():
    async with engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as session:
        session.add_all(SEED_PERSONAS)
        session.add_all(SEED_PRODUCTS)
        await session.commit()
        print("Seeded 4 age-group personas and 5 oral-care products.")


if __name__ == "__main__":
    asyncio.run(seed())