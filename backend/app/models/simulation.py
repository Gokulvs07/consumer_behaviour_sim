from datetime import datetime, timezone
from sqlalchemy import DateTime, Float, ForeignKey, Integer, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from pgvector.sqlalchemy import Vector
from app.core.config import settings
from app.core.database import Base


class SimulationRun(Base):
    __tablename__ = "simulation_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    persona_id: Mapped[int] = mapped_column(ForeignKey("user_profiles.id"), nullable=False, index=True)
    budget_allocated: Mapped[float] = mapped_column(Float, nullable=False)
    total_spent: Mapped[float] = mapped_column(Float, default=0.0)
    remaining_budget: Mapped[float] = mapped_column(Float, default=0.0)
    final_basket: Mapped[list] = mapped_column(JSONB, default=list)
    decision_trace: Mapped[list] = mapped_column(JSONB, default=list)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )


class ProductEvaluation(Base):
    __tablename__ = "product_evaluations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("simulation_runs.id"), nullable=False, index=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), nullable=False)
    raw_reaction: Mapped[str] = mapped_column(Text, nullable=False)
    reaction_embedding: Mapped[list[float]] = mapped_column(Vector(settings.embedding_dim))
    ssr_probabilities: Mapped[dict] = mapped_column(JSONB, default=dict)
    base_utility_u0: Mapped[float] = mapped_column(Float, nullable=False)