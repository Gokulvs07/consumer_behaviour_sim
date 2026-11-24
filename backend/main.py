from app import engine
from contextlib import asynccontextmanager
from fastapi import Depends, FastAPI, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.core.database import Base, engine, get_db
from app.engine.simulator import get_scorer, run_persona_simulation
from app.models.persona import UserProfile
from app.models.product import Product
from app.models.simulation import ProductEvaluation, SimulationRun
from app.schemas import (
    BatchSimulationRequest,
    PersonaOut,
    ProductOut,
    SimulationDetailOut,
    SimulationRequest,
    SimulationRunOut,
)
from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel, Field

@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await conn.execute(
            text("ALTER TABLE evaluation_cache ADD COLUMN IF NOT EXISTS content_hash VARCHAR(64) NOT NULL DEFAULT ''")
        )
    get_scorer()
    yield


app = FastAPI(
    title="Consumer Behavior Simulation API",
    description="LLM Persona Roleplay + Semantic Similarity Rating (SSR) + Marginal Utility Engine",
    version="0.1.0",
    lifespan=lifespan,
)


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/personas", response_model=list[PersonaOut])
async def list_personas(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(UserProfile).order_by(UserProfile.id))
    return result.scalars().all()


@app.get("/products", response_model=list[ProductOut])
async def list_products(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Product).order_by(Product.id))
    return result.scalars().all()



@app.post("/simulations/batch", response_model=list[SimulationRunOut])
async def run_batch_simulation(req: BatchSimulationRequest, db: AsyncSession = Depends(get_db)):
    stmt = select(UserProfile).order_by(UserProfile.id)
    if req.age_group is not None:
        stmt = stmt.where(UserProfile.age_group == req.age_group)

    personas = (await db.execute(stmt)).scalars().all()
    if not personas:
        raise HTTPException(status_code=404, detail="No matching personas found.")

    runs = []
    for persona in personas:
        run = await run_persona_simulation(
            session=db,
            persona_id=persona.id,
            budget_override=req.budget_override,
        )
        runs.append(run)
    return runs


@app.get("/simulations/{run_id}", response_model=SimulationDetailOut)
async def get_simulation(run_id: int, db: AsyncSession = Depends(get_db)):
    sim_run = await db.get(SimulationRun, run_id)
    if not sim_run:
        raise HTTPException(status_code=404, detail=f"SimulationRun {run_id} not found.")

    evals = (
        await db.execute(
            select(ProductEvaluation)
            .where(ProductEvaluation.run_id == run_id)
            .order_by(ProductEvaluation.product_id)
        )
    ).scalars().all()

    return SimulationDetailOut(
        **SimulationRunOut.model_validate(sim_run).model_dump(),
        evaluations=evals,
    )

