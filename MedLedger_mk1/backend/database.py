import os

import motor.motor_asyncio
import config

client = motor.motor_asyncio.AsyncIOMotorClient(config.MONGO_URI)


async def get_collection(collection_name: str):
    return db[collection_name]


# client = motor.AsyncIOMotorClient(os.getenv("MONGODB_URI", "mongodb://localhost:27017"))
db = client[os.getenv("MONGO_DB", "medledger_analytics")]


def get_audit_collection():
    return db["audit_trail"]
