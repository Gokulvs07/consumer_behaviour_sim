import enum
from sqlalchemy import Enum, Float, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base


class AgeGroup(str, enum.Enum):
    GEN_Z = "18-24"
    MILLENNIAL = "25-40"
    GEN_X = "41-56"
    SENIOR = "57+"


class UserProfile(Base):
    __tablename__ = "user_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    age: Mapped[int] = mapped_column(Integer, nullable=False)
    age_group: Mapped[AgeGroup] = mapped_column(Enum(AgeGroup), nullable=False, index=True)
    occupation: Mapped[str] = mapped_column(String(100), nullable=False)
    monthly_budget: Mapped[float] = mapped_column(Float, nullable=False)

    # Economic parameters for the Marginal Utility engine
    price_sensitivity: Mapped[float] = mapped_column(Float, default=1.0)      # lambda (λ)
    reservation_threshold: Mapped[float] = mapped_column(Float, default=15.0) # min MU/$ to buy

    # Psychological & behavioral context for LLM elicitation
    bio: Mapped[str] = mapped_column(Text, nullable=False)
    traits: Mapped[dict] = mapped_column(JSONB, default=dict)