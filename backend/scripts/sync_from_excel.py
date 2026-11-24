import argparse
import asyncio
from pathlib import Path
import openpyxl
from sqlalchemy import delete, select

from app.core.database import AsyncSessionLocal
from app.models.persona import AgeGroup, UserProfile
from app.models.product import Product


def _clean_str(val) -> str:
    return "" if val is None else str(val).strip()


def _clean_float(val, default: float) -> float:
    if val is None or str(val).strip() == "":
        return default
    return float(val)


def _clean_int(val):
    if val is None or str(val).strip() == "":
        return None
    return int(float(val))


def load_products_from_sheet(ws) -> list[dict]:
    items = []
    # Data starts at row 8 (headers at row 7; rows 1-6 are banner, note, and formula summary)
    for row in ws.iter_rows(min_row=8, values_only=True):
        if not any(row):
            continue
        pid, _sku, name, _brand, price, category, description, action = (list(row) + [None] * 8)[:8]
        name_s = _clean_str(name)
        if not name_s:
            continue
        items.append({
            "id": _clean_int(pid),
            "name": name_s,
            "price": _clean_float(price, 100.0),
            "category": _clean_str(category) or "general",
            "description": _clean_str(description),
            "action": (_clean_str(action) or "UPSERT").upper(),
        })
    return items


def load_personas_from_sheet(ws) -> list[dict]:
    items = []
    # Data starts at row 8 (headers at row 7; rows 1-6 are banner, note, and formula summary)
    for row in ws.iter_rows(min_row=8, values_only=True):
        if not any(row):
            continue
        pe_id, name, age_group, occupation, budget, sensitivity, satiation, threshold, bio, action = (
            list(row) + [None] * 10
        )[:10]
        name_s = _clean_str(name)
        if not name_s:
            continue
        items.append({
            "id": _clean_int(pe_id),
            "name": name_s,
            "age_group": AgeGroup(_clean_str(age_group) or "25-40"),
            "occupation": _clean_str(occupation) or "Consumer",
            "monthly_budget": _clean_float(budget, 1000.0),
            "price_sensitivity": _clean_float(sensitivity, 0.5),
            "satiation": _clean_float(satiation, 0.5),
            "reservation_threshold": _clean_float(threshold, 15.0),
            "bio": _clean_str(bio),
            "action": (_clean_str(action) or "UPSERT").upper(),
        })
    return items


async def sync_workbook(xlsx_path: Path, prune_missing: bool = False) -> dict:
    wb = openpyxl.load_workbook(xlsx_path, data_only=True)
    prod_items = load_products_from_sheet(wb["Products"]) if "Products" in wb.sheetnames else []
    per_items = load_personas_from_sheet(wb["Personas"]) if "Personas" in wb.sheetnames else []

    stats = {
        "products_upserted": 0,
        "products_deleted": 0,
        "personas_upserted": 0,
        "personas_deleted": 0,
    }

    async with AsyncSessionLocal() as session:
        # 1. Sync Products
        kept_product_ids = set()
        for item in prod_items:
            existing = None
            if item["id"] is not None:
                existing = (await session.execute(select(Product).where(Product.id == item["id"]))).scalar_one_or_none()
            if existing is None:
                existing = (await session.execute(select(Product).where(Product.name == item["name"]))).scalar_one_or_none()

            if item["action"] == "DELETE":
                if existing is not None:
                    await session.delete(existing)
                    stats["products_deleted"] += 1
                continue

            if existing is None:
                existing = Product(
                    name=item["name"],
                    price=item["price"],
                    category=item["category"],
                    description=item["description"],
                )
                session.add(existing)
                await session.flush()
            else:
                existing.name = item["name"]
                existing.price = item["price"]
                existing.category = item["category"]
                existing.description = item["description"]

            kept_product_ids.add(existing.id)
            stats["products_upserted"] += 1

        if prune_missing and kept_product_ids:
            res = await session.execute(delete(Product).where(Product.id.notin_(kept_product_ids)))
            stats["products_deleted"] += res.rowcount or 0

        # 2. Sync Personas
        kept_persona_ids = set()
        for item in per_items:
            existing = None
            if item["id"] is not None:
                existing = (await session.execute(select(UserProfile).where(UserProfile.id == item["id"]))).scalar_one_or_none()
            if existing is None:
                existing = (await session.execute(select(UserProfile).where(UserProfile.name == item["name"]))).scalar_one_or_none()

            if item["action"] == "DELETE":
                if existing is not None:
                    await session.delete(existing)
                    stats["personas_deleted"] += 1
                continue

            if existing is None:
                existing = UserProfile(
                    name=item["name"],
                    age_group=item["age_group"],
                    occupation=item["occupation"],
                    monthly_budget=item["monthly_budget"],
                    price_sensitivity=item["price_sensitivity"],
                    satiation=item["satiation"],
                    reservation_threshold=item["reservation_threshold"],
                    bio=item["bio"],
                )
                session.add(existing)
                await session.flush()
            else:
                existing.name = item["name"]
                existing.age_group = item["age_group"]
                existing.occupation = item["occupation"]
                existing.monthly_budget = item["monthly_budget"]
                existing.price_sensitivity = item["price_sensitivity"]
                existing.satiation = item["satiation"]
                existing.reservation_threshold = item["reservation_threshold"]
                existing.bio = item["bio"]

            kept_persona_ids.add(existing.id)
            stats["personas_upserted"] += 1

        if prune_missing and kept_persona_ids:
            res = await session.execute(delete(UserProfile).where(UserProfile.id.notin_(kept_persona_ids)))
            stats["personas_deleted"] += res.rowcount or 0

        await session.commit()

    return stats


def main():
    parser = argparse.ArgumentParser(description="Sync Products and Personas from Excel into PostgreSQL.")
    parser.add_argument("--file", type=Path, required=True, help="Path to source-of-truth .xlsx file")
    parser.add_argument("--prune-missing", action="store_true", help="Delete DB rows absent from the sheet")
    args = parser.parse_args()
    summary = asyncio.run(sync_workbook(args.file, prune_missing=args.prune_missing))
    print("Sync complete:", summary)


if __name__ == "__main__":
    main()