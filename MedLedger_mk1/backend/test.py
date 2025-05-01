import asyncio
from motor.motor_asyncio import AsyncIOMotorClient

async def check():
    cli = AsyncIOMotorClient("mongodb://localhost:27017")
    db = cli["medledger_analytics"]
    docs = await db["vitals"].find().to_list(3)
    for d in docs:
        print(d)

if __name__ == "__main__":
    asyncio.run(check())
