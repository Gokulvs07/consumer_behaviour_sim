from app.core.llm import generate_persona_response
from app.models.persona import UserProfile
from app.models.product import Product


def build_system_prompt(persona: UserProfile) -> str:
    priorities = ", ".join(persona.traits.get("priorities", []))
    loyalty = persona.traits.get("brand_loyalty", "medium")
    return (
        f"You are roleplaying as {persona.name}, a {persona.age}-year-old {persona.occupation} "
        f"(age group: {persona.age_group.value}).\n"
        f"Background: {persona.bio}\n"
        f"Monthly personal care budget: ₹{persona.monthly_budget:.0f}. "
        f"Brand loyalty: {loyalty}. Top priorities: {priorities}.\n\n"
        "Respond strictly in first person as this real consumer. Be honest, specific, and blunt "
        "about whether you would actually spend your own money on the product. "
        "Do NOT give a numerical rating (no 1-5 or out-of-10 scores). Keep it to 2-3 natural sentences."
    )


def build_product_prompt(product: Product) -> str:
    return (
        f"You are browsing a store and see this product:\n"
        f"- Product: {product.name} ({product.brand})\n"
        f"- Category: {product.category}\n"
        f"- Price: ₹{product.price:.0f}\n"
        f"- Description: {product.description}\n\n"
        "What is your immediate gut reaction? Would you buy it today, and why?"
    )


async def elicit_reaction(persona: UserProfile, product: Product) -> str:
    system_prompt = build_system_prompt(persona)
    user_prompt = build_product_prompt(product)
    return await generate_persona_response(system_prompt, user_prompt)