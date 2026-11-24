from datetime import datetime
from pydantic import BaseModel, ConfigDict
from app.models.persona import AgeGroup


class PersonaOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    age: int
    age_group: AgeGroup
    occupation: str
    monthly_budget: float
    price_sensitivity: float
    reservation_threshold: float
    bio: str
    traits: dict


class ProductOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    brand: str
    category: str
    price: float
    satiation_alpha: float
    description: str
    attributes: dict


class SimulationRequest(BaseModel):
    persona_id: int
    budget_override: float | None = None


class BatchSimulationRequest(BaseModel):
    age_group: AgeGroup | None = None
    budget_override: float | None = None


class ProductEvaluationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    product_id: int
    raw_reaction: str
    ssr_probabilities: dict
    base_utility_u0: float


class SimulationRunOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    persona_id: int
    budget_allocated: float
    total_spent: float
    remaining_budget: float
    final_basket: list[dict]
    decision_trace: list[dict]
    created_at: datetime


class SimulationDetailOut(SimulationRunOut):
    evaluations: list[ProductEvaluationOut] = []