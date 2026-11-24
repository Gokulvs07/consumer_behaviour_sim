import asyncio
from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.engine.simulator import run_persona_simulation
from app.models.persona import UserProfile


async def main():
    async with AsyncSessionLocal() as session:
        personas = (
            await session.execute(select(UserProfile).where(UserProfile.name.in_(["Aarav", "Meenakshi"])))
        ).scalars().all()

        for persona in personas:
            print(f"\n{'='*65}")
            print(f"RUNNING E2E SIMULATION: {persona.name} ({persona.age_group.value}, Budget: ₹{persona.monthly_budget:.0f})")
            print(f"{'='*65}")

            run = await run_persona_simulation(session, persona.id)

            print(f"Saved SimulationRun ID: {run.id}")
            print(f"Spent: ₹{run.total_spent:.2f} / ₹{run.budget_allocated:.2f} (Remaining: ₹{run.remaining_budget:.2f})\n")

            print("FINAL BASKET:")
            for item in run.final_basket:
                print(f"  - {item['quantity']}x {item['product_name']} @ ₹{item['unit_price']:.0f} = ₹{item['subtotal']:.0f}")

            print("\nDECISION TRACE:")
            for step in run.decision_trace:
                if step["action"] == "BUY":
                    print(
                        f"  Step {step['step']}: BUY {step['product_name']} (unit #{step['unit_number']}) | "
                        f"MU={step['marginal_utility']} | Value={step['value_score']} | Left=₹{step['remaining_budget']}"
                    )
                else:
                    print(f"  Step {step['step']}: STOP — {step['reason']}")


if __name__ == "__main__":
    asyncio.run(main())