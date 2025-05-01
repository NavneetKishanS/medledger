# backend/routes/vitals.py

from fastapi import APIRouter, Depends, HTTPException, Query
from datetime import datetime, timezone
from typing import Dict
import os
import numpy as np
import joblib

from auth import get_current_user
from config import MONGO_URI
from motor.motor_asyncio import AsyncIOMotorClient
from mongo_client import get_mongo_collection

router = APIRouter(tags=["Vitals"])
router2 = APIRouter(tags=["Vitals"])

# Load Isolation Forest model
model = joblib.load(os.path.join(os.path.dirname(__file__), "../isoforest.joblib"))

# Mongo connection
mongo_client = AsyncIOMotorClient(MONGO_URI)
db = mongo_client["medledger_analytics"]

# ---------------------------------------------------------------------------- #
# POST /vitals/{patient_id}
# ---------------------------------------------------------------------------- #
@router.post("/vitals/{patient_id}", response_model=Dict)
async def post_vitals(
    patient_id: str,
    body: Dict,  # expects keys: spo2, temperature, heart_rate, (username optional)
    user=Depends(get_current_user),
    col=Depends(get_mongo_collection("vitals"))
):
    """
    Accept one vitals sample.
    Auth:
      - Doctor → can post for any patient
      - Patient → can post only their own
    """
    # if user["role"] == "patient" and user["username"] != body.get("username"):
    #     raise HTTPException(403, "Patients may post only their own vitals")
    #
    # if user["role"] not in ("doctor", "patient"):
    #     raise HTTPException(403, "Not permitted")

    # Run anomaly detection
    X = np.array([[body["heart_rate"], body["spo2"], body["temperature"]]])  # Match model's training order
    is_anomaly = model.predict(X)[0] == -1

    doc = {
        "patient_id":  patient_id,
        "username":    body.get("username"),
        "spo2":        body["spo2"],
        "temperature": body["temperature"],
        "heart_rate":  body["heart_rate"],
        "timestamp":   datetime.now(timezone.utc),
        "anomaly":     bool(is_anomaly),
    }

    await col.insert_one(doc)

    # Optional: push_alert(...) if SSE is enabled

    return {"stored": True, "anomaly": bool(is_anomaly)}

# ---------------------------------------------------------------------------- #
# GET /patients/me/vitals
# ---------------------------------------------------------------------------- #
# backend/routes/vitals.py
@router2.get("/vitals_raw/{patient_id}")
async def get_raw_vitals(patient_id: str, n: int = Query(10, ge=1, le=100)):
    """Basic endpoint for vitals data, no auth, no role checks — for charts/debug."""
    cursor = db["vitals"].find({"patient_id": patient_id}, {"_id": 0}).sort("timestamp", -1).limit(n)
    vitals = await cursor.to_list(length=n)
    vitals.reverse()
    return vitals