import asyncio
from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.engine.elicitor import elicit_reaction
from app.engine.ssr_scorer import SSRScorer
from app.models.persona import UserProfile
from app.models.product import Product


async def main():
    scorer = SSRScorer()  # Downloads BAAI/bge-small-en-v1.5 (~130MB) on first run

    async with AsyncSessionLocal() as session:
        personas = (await session.execute(select(UserProfile).where(UserProfile.name.in_(["Aarav", "Meenakshi"])))).scalars().all()
        products = (await session.execute(select(Product))).scalars().all()

    for persona in personas:
        print(f"\n{'='*60}")
        print(f"PERSONA: {persona.name} ({persona.age_group.value}, Budget: ₹{persona.monthly_budget:.0f})")
        print(f"{'='*60}")
        for product in products:
            reaction = await elicit_reaction(persona, product)
            result = scorer.score_reaction(reaction)
            print(f"\n[{product.name} - ₹{product.price:.0f}]")
            print(f"  Reaction : {reaction}")
            print(f"  SSR Probs: {result.probabilities}")
            print(f"  Likert   : {result.expected_likert}/5.0  -->  Base Utility (U0): {result.base_utility_u0}/100")


if __name__ == "__main__":
    asyncio.run(main())