from sqlalchemy import Float, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base


class Product(Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    brand: Mapped[str] = mapped_column(String(100), nullable=False)
    category: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    price: Mapped[float] = mapped_column(Float, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)

    # Satiation decay rate (alpha) for diminishing marginal utility
    satiation_alpha: Mapped[float] = mapped_column(Float, default=1.2)
    attributes: Mapped[dict] = mapped_column(JSONB, default=dict)