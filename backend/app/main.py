from contextlib import asynccontextmanager
from fastapi import Depends, FastAPI, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from fastapi.middleware.cors import CORSMiddleware
from app.core.database import get_db
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


from app.engine.market_analyzer import run_market_analysis
from app.models.persona import AgeGroup

from app.core.database import Base, engine, get_db
from app.engine.cache import EvaluationCache  # noqa: F401
from app.engine.pricing_lab import run_price_sweep
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

class ProductCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=120)
    price: float = Field(..., gt=0)
    brand: str = Field(default="", max_length=80)
    category: str = Field(default="oral_care", max_length=60)
    description: str = Field(..., min_length=5, max_length=500)

app = FastAPI(
    title="Consumer Behavior Simulation API",
    description="LLM Persona Roleplay + Semantic Similarity Rating (SSR) + Marginal Utility Engine",
    version="0.1.0",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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

@app.post("/products", status_code=201)
async def create_product(payload: ProductCreate, db: AsyncSession = Depends(get_db)):
    clean_name = payload.name.strip()
    clean_brand = payload.brand.strip() or clean_name.split()[0]

    new_product = Product(
        name=clean_name,
        brand=clean_brand,  # <-- must be passed here
        category=payload.category.strip() or "general",
        price=payload.price,
        description=payload.description.strip(),
    )
    db.add(new_product)
    await db.commit()
    await db.refresh(new_product)
    return {
        "id": new_product.id,
        "name": new_product.name,
        "brand": new_product.brand,
        "price": new_product.price,
        "category": new_product.category,
        "description": new_product.description,
    }

@app.post("/simulations/run", response_model=SimulationRunOut)
async def create_simulation(req: SimulationRequest, db: AsyncSession = Depends(get_db)):
    try:
        return await run_persona_simulation(
            session=db,
            persona_id=req.persona_id,
            budget_override=req.budget_override,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.post("/simulations/run", response_model=SimulationRunOut)
async def create_simulation(req: SimulationRequest, db: AsyncSession = Depends(get_db)):
    try:
        return await run_persona_simulation(
            session=db,
            persona_id=req.persona_id,
            budget_override=req.budget_override,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


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

class MarketAnalysisRequest(BaseModel):
    product_ids: list[int]
    age_group: AgeGroup | None = None


@app.post("/market-analysis/compare")
async def compare_products(req: MarketAnalysisRequest, db: AsyncSession = Depends(get_db)):
    try:
        return await run_market_analysis(
            session=db,
            product_ids=req.product_ids,
            age_group=req.age_group,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

class PricingSweepRequest(BaseModel):
    target_product_id: int
    competitor_ids: list[int]
    min_pct: float = -30.0
    max_pct: float = 30.0
    steps: int = 7
    age_group: AgeGroup | None = None
    force_refresh: bool = False
    choice_model: str = "deterministic"


@app.post("/pricing-lab/sweep")
async def pricing_lab_sweep(req: PricingSweepRequest, db: AsyncSession = Depends(get_db)):
    try:
        return await run_price_sweep(
            session=db,
            target_product_id=req.target_product_id,
            competitor_ids=req.competitor_ids,
            min_pct=req.min_pct,
            max_pct=req.max_pct,
            steps=req.steps,
            age_group=req.age_group,
            force_refresh=req.force_refresh,
            choice_model=req.choice_model,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))