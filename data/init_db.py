import os
import json
import asyncio
from pathlib import Path
from sqlalchemy import select, func
from backend.database import engine, AsyncSessionLocal, Base
from backend.models import Fact


async def init_database_and_seed(seed_file_path: str = "data/seed_facts.json"):
    """
    Creates database tables and loads seed facts if the database is empty or new facts exist.
    """
    # 1. Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # 2. Check seed file
    seed_path = Path(seed_file_path)
    if not seed_path.exists():
        print(f"Seed file {seed_file_path} not found. Skipping seeding.")
        return

    with open(seed_path, "r", encoding="utf-8") as f:
        facts_data = json.load(f)

    # 3. Seed facts
    async with AsyncSessionLocal() as session:
        # Check current count
        count_stmt = select(func.count(Fact.id))
        res = await session.execute(count_stmt)
        current_count = res.scalar() or 0

        if current_count < len(facts_data):
            print(f"Seeding database with verified facts ({len(facts_data)} facts in seed dataset)...")
            
            # Fetch existing titles to avoid duplicate insertions
            existing_titles_res = await session.execute(select(Fact.title))
            existing_titles = set(existing_titles_res.scalars().all())

            added_count = 0
            for item in facts_data:
                if item["title"] not in existing_titles:
                    fact = Fact(
                        title=item["title"],
                        teaser=item["teaser"],
                        fact_text=item["fact"],
                        explanation=item["explanation"],
                        category=item["category"],
                        source_name=item["source_name"],
                        source_url=item["source_url"],
                        interestingness_score=item.get("interestingness_score", 5),
                        verification_status=item.get("verification_status", "verified"),
                        is_active=True
                    )
                    session.add(fact)
                    added_count += 1

            await session.commit()
            print(f"Successfully added {added_count} new verified facts. Total in DB: {current_count + added_count}")
        else:
            print(f"Database already contains {current_count} facts. Seeding not required.")


if __name__ == "__main__":
    asyncio.run(init_database_and_seed())
