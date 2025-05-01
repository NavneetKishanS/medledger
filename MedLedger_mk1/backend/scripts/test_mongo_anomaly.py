import asyncio
import os
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

load_dotenv()

async def main():
    uri = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
    dbname = os.getenv("MONGO_DB", "medledger_analytics")

    client = AsyncIOMotorClient(uri)
    col = client[dbname]["anomaly_vitals"]

    docs = await col.find().sort("timestamp", -1).to_list(5)
    for doc in docs:
        print(doc)

if __name__ == "__main__":
    asyncio.run(main())