
import joblib
from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException
from pydantic import BaseModel, Field
from datetime import datetime
from pathlib import Path
import pandas as pd
from alert_buffer import add_alert
from mongo_client import get_mongo_collection

from config import FHIR_SERVER_URL, USERNAME_SYSTEM
from auth import get_current_user

router = APIRouter(prefix="/vitals", tags=["vitals"])


model_path = Path(__file__).resolve().parent.parent / "isoforest.joblib"
iso_forest = joblib.load(model_path)


class VitalBase(BaseModel):
    spo2: float = Field(..., ge=0, le=100, description="SpO₂ (percent)")
    temperature: float = Field(..., description="Body temperature °C")
    heart_rate: int = Field(..., description="Heart rate bpm")
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class VitalIn(VitalBase):
    """Full payload with an explicit patient_id (internal/JWT routes)."""
    patient_id: str = Field(..., description="FHIR Patient.id")

class VitalInWithNone(VitalBase):
    """Same schema, but patient_id can be omitted by the caller."""
    patient_id: str | None = None


async def send_anomaly_alert(patient_id: str, vitals: VitalBase) -> None:
    """Stub that would fan‑out to e‑mail / SMS / websocket etc."""
    print(
        f"🚨 ANOMALY 🚨  patient={patient_id} "
        f"SpO₂={vitals.spo2}, Temp={vitals.temperature}, HR={vitals.heart_rate} "
        f"@ {vitals.timestamp.isoformat()}"
    )


@router.post("/", summary="Ingest periodic vitals and flag anomalies")
async def ingest_vitals(
    v: VitalInWithNone,
    bg: BackgroundTasks,
    current_user: dict = Depends(get_current_user),
    col = Depends(get_mongo_collection("anomaly_vitals")),  # ✅ new collection
):

    if current_user["role"] != "patient":
        raise HTTPException(status_code=403, detail="Not permitted")

    features = [[
        v.heart_rate,
        v.spo2,
        v.temperature
    ]]

    try:
        pred = int(iso_forest.predict(features)[0])
    except Exception as exc:
        raise HTTPException(500, f"Anomaly detection failed: {exc}")

    is_anomaly = (pred == -1)
    username    = current_user["username"]

    record = {
        "spo2":        float(v.spo2),
        "temperature": float(v.temperature),
        "heart_rate":  int(v.heart_rate),
        "timestamp":   v.timestamp.isoformat(),
        "anomaly":     is_anomaly,
    }

    add_alert(username, record)

    if is_anomaly:
        bg.add_task(send_anomaly_alert, username, v)

    print(
        f"Vitals | user={username} | "
        f"SpO₂={v.spo2}  Temp={v.temperature}  HR={v.heart_rate} | "
        f"{'ANOMALY' if is_anomaly else 'normal'} @ {v.timestamp.isoformat()}"
    )

    await col.insert_one({
        "username": username,
        "patient_id": v.patient_id,
        "spo2": v.spo2,
        "temperature": v.temperature,
        "heart_rate": v.heart_rate,
        "timestamp": v.timestamp,
        "anomaly": is_anomaly
    })

    return record