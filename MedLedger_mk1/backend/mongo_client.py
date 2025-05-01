import os
from fastapi import FastAPI, Request, Depends
from motor.motor_asyncio import AsyncIOMotorClient
from contextlib import asynccontextmanager
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from sync_fhir import ensure_fhir_sync

scheduler = AsyncIOScheduler()

def schedule_fhir_sync(db):
    async def sync_wrapper():
        await ensure_fhir_sync(db)

    scheduler.add_job(
        sync_wrapper,
        trigger=IntervalTrigger(minutes=2),
        name="fhir_resync_job"
    )

@asynccontextmanager
async def mongo_lifespan(app: FastAPI):
    uri = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
    client = AsyncIOMotorClient(uri, tz_aware=True)
    db = client[os.getenv("MONGO_DB", "medledger_analytics")]
    app.state.mongo = db

    await ensure_fhir_sync(db)

    schedule_fhir_sync(db)
    scheduler.start()

    yield

    scheduler.shutdown()
    client.close()

def get_mongo_collection(name: str):
    def _getter(request: Request):
        return request.app.state.mongo[name]
    return _getter

async def get_mongo_db():
    uri = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
    client = AsyncIOMotorClient(uri, tz_aware=True)
    db = client[os.getenv("MONGO_DB", "medledger_analytics")]
    return db
