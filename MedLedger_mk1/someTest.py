from motor.motor_asyncio import AsyncIOMotorClient
import asyncio

async def check_vitals():
    client = AsyncIOMotorClient("mongodb://localhost:27017")
    db = client["medledger_analytics"]
    cursor = db["vitals"].find({"patient_id": "4"}).sort("timestamp", -1).limit(10)
    results = await cursor.to_list(length=10)
    for doc in results:
        print(doc)

asyncio.run(check_vitals())
