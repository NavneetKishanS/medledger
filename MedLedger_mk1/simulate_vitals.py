# simulate_vitals.py

import asyncio
import random
import os
from datetime import datetime, timezone
from motor.motor_asyncio import AsyncIOMotorClient
import joblib
import numpy as np

# --- MongoDB Setup ---
MONGO_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
DB_NAME = os.getenv("MONGO_DB", "medledger_analytics")

# --- Load ML model ---
# MODEL_PATH = os.getenv("MODEL_PATH", "isoforest.joblib")
model = joblib.load("backend/isoforest.joblib")

# --- Random Vital Generators ---
def random_spo2():
    return round(random.uniform(90, 100), 1)

def random_temp():
    return round(random.uniform(36.0, 38.5), 1)

def random_heart_rate():
    return random.randint(55, 110)

# --- Main Logic ---
async def simulate_vitals():
    print("[🔌] Connecting to MongoDB…")
    client = AsyncIOMotorClient(MONGO_URI, tz_aware=True)
    db = client[DB_NAME]

    # Get all patients
    patients = await db["patients_basic"].find({}).to_list(length=1000)
    if not patients:
        print("[❌] No patients found!")
        return

    print(f"[📋] Found {len(patients)} patients.")

    while True:
        patient = random.choice(patients)
        username = patient.get("username")
        patient_id = patient.get("patient_id")

        if not username:
            print("[⚠️] Skipping patient with no username.")
            continue

        # Generate random vitals
        spo2 = random_spo2()
        temp = random_temp()
        hr = random_heart_rate()

        # Prepare feature vector
        features = np.array([[hr, spo2, temp]])
        pred = model.predict(features)
        anomaly = bool(pred[0] == -1)

        # Insert into vitals collection
        vitals_doc = {
            "username": username,
            "patient_id": patient_id,
            "spo2": spo2,
            "temperature": temp,
            "heart_rate": hr,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "anomaly": anomaly
        }

        await db["vitals"].insert_one(vitals_doc)

        if anomaly:
            print(f"[🚨] Anomalous vitals inserted for {username}: {vitals_doc}")
        else:
            print(f"[✅] Normal vitals inserted for {username}: {vitals_doc}")

        await asyncio.sleep(2)  # Every 2 seconds

if __name__ == "__main__":
    asyncio.run(simulate_vitals())
