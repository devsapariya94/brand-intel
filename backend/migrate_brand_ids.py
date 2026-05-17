#!/usr/bin/env python3
"""Convert legacy raw_hits.brand_id string values to ObjectId."""
import asyncio
import os
from pathlib import Path

from bson import ObjectId
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient


async def main():
    load_dotenv(Path(__file__).parent / ".env")
    client = AsyncIOMotorClient(os.getenv("MONGODB_URI", "mongodb://localhost:27017"))
    db = client.brand_intel

    updated = 0
    skipped = 0

    cursor = db.raw_hits.find({"brand_id": {"$type": "string"}})
    async for hit in cursor:
        brand_id = hit.get("brand_id")
        if not ObjectId.is_valid(brand_id):
            skipped += 1
            continue

        result = await db.raw_hits.update_one(
            {"_id": hit["_id"]},
            {"$set": {"brand_id": ObjectId(brand_id)}}
        )
        updated += result.modified_count

    print(f"raw_hits.brand_id migration complete: updated={updated}, skipped={skipped}")
    client.close()


if __name__ == "__main__":
    asyncio.run(main())
