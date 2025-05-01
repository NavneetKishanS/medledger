import os
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from routes import vitals as vitals_routes
from routes import users, patients, doctor, anomaly, audit
from routes import sse as sse_routes
from sync_fhir import ensure_fhir_sync, update_patient_ids_from_usernames, start_scheduler, wait_for_fhir_server


@asynccontextmanager
async def mongo_lifespan(app: FastAPI):
    uri = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
    client = AsyncIOMotorClient(uri, tz_aware=True)
    db = client[os.getenv("MONGO_DB", "medledger_analytics")]
    app.state.mongo = db
    print("[✅] Connected to MongoDB.")
    yield
    client.close()


app = FastAPI(lifespan=mongo_lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(users.router, tags=["Authentication"])
app.include_router(patients.router, prefix="/patients", tags=["Patients"])
app.include_router(doctor.router, prefix="/doctor", tags=["Doctor"])
app.include_router(anomaly.router)
app.include_router(sse_routes.router)
app.include_router(vitals_routes.router, prefix="/vitals", tags=["Vitals"])
app.include_router(vitals_routes.router2)
app.include_router(audit.router)

FHIR_BASE = os.getenv("FHIR_SERVER_URL", "http://localhost:8080")


@app.on_event("startup")
async def startup_event():
    db = app.state.mongo

    print("[⏳] Checking FHIR server availability…")
    metadata_url = await wait_for_fhir_server(FHIR_BASE)
    if not metadata_url:
        print("[❌] FHIR server not reachable – startup sync skipped (scheduler WILL still try later).")
    else:
        print("[🚀] FHIR is up – running immediate sync…")
        await ensure_fhir_sync(db)
        await update_patient_ids_from_usernames(db)

    start_scheduler(db)


@app.get("/")
async def root():
    return {"message": "FastAPI + FHIR + Blockchain Audit running"}
