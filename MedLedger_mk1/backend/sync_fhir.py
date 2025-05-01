"""
Mirror every locally-cached FHIR resource in Mongo back to the live FHIR
server.  A doc is considered “fixed” when GET /<type>/<fhir_id> returns 200;
otherwise we POST its `payload` again.

Collections mirrored   →   FHIR resourceType
----------------------------------------------------
patients_basic         →   Patient
observations           →   Observation
allergies              →   AllergyIntolerance
conditions             →   Condition
immunizations          →   Immunization
treatments             →   MedicationRequest
"""

from __future__ import annotations

import asyncio, os
from datetime import datetime
from typing import Dict, List

import httpx
from motor.motor_asyncio import AsyncIOMotorDatabase

from dotenv import load_dotenv
import config

load_dotenv()

from config import FHIR_SERVER_URL, USERNAME_SYSTEM

RESOURCE_COLLECTIONS: Dict[str, str] = {
    "patients_basic": "Patient",
    "observations": "Observation",
    "allergies": "AllergyIntolerance",
    "conditions": "Condition",
    "immunizations": "Immunization",
    "treatments": "MedicationRequest",
}


async def wait_for_fhir_server(base_url: str, retries: int = 20, delay: int = 3) -> bool:
    """
    Return True when <base_url>/metadata (or /fhir/metadata) responds 200.
    Try `retries`× every `delay`s; otherwise return False.
    """
    base_url = base_url.rstrip("/")
    probe_urls = [f"{base_url}/metadata"]
    if not base_url.endswith("/fhir"):
        probe_urls.append(f"{base_url}/fhir/metadata")

    async with httpx.AsyncClient(timeout=4) as cli:
        for _ in range(retries):
            for url in probe_urls:
                try:
                    print(f"[probe] GET {url}")
                    r = await cli.get(url)
                    if r.status_code == 200:
                        print(f"[✅] FHIR reachable at {url}")
                        return True
                except Exception as e:
                    print(f"[✘] {url} → {e}")
            await asyncio.sleep(delay)
    print(" FHIR server NOT reachable.")
    return False


async def ensure_fhir_sync(db: AsyncIOMotorDatabase) -> None:
    """
    * for each doc in every mirrored collection:
        – if `fhir_id` exists and GET returns 200 → mark synced True
        – else  POST payload again, store new id, timestamps, etc.
    """
    if not await wait_for_fhir_server(FHIR_SERVER_URL, retries=10, delay=3):
        print("FHIR unavailable; aborting")
        return

    async with httpx.AsyncClient(timeout=15) as cli:
        for coll_name, fhir_type in RESOURCE_COLLECTIONS.items():
            coll = db[coll_name]
            async for doc in coll.find():
                fhir_id = doc.get("fhir_id")
                payload = doc.get("payload") or {}
                doc_id = doc["_id"]

                if payload.get("resourceType") != fhir_type:
                    print(f"[⚠] {coll_name}:{doc_id} type mismatch – skipped")
                    continue

                try:

                    already = False
                    if fhir_id:
                        r = await cli.get(
                            f"{FHIR_SERVER_URL}/{fhir_type}/{fhir_id}",
                            headers={"Accept": "application/fhir+json"}
                        )
                        if r.status_code == 200:
                            already = True
                            await coll.update_one(
                                {"_id": doc_id},
                                {"$set": {"synced": True, "error": None}}
                            )

                    if already:
                        continue
                    if not payload:
                        raise ValueError("payload missing")

                    print(f"[→] Replaying {fhir_type} {doc_id} …")
                    r = await cli.post(
                        f"{FHIR_SERVER_URL}/{fhir_type}",
                        json=payload,
                        headers={"Content-Type": "application/fhir+json"}
                    )
                    r.raise_for_status()
                    new_id = r.json()["id"]

                    await coll.update_one(
                        {"_id": doc_id},
                        {"$set": {
                            "fhir_id": new_id,
                            "synced": True,
                            "error": None,
                            "resynced_at": datetime.utcnow()
                        }}
                    )
                    print(f"[✔] {fhir_type} {doc_id} → FHIR ID {new_id}")

                except Exception as exc:
                    await coll.update_one(
                        {"_id": doc_id},
                        {"$set": {
                            "synced": False,
                            "error": str(exc),
                            "resynced_failed_at": datetime.utcnow()
                        }}
                    )
                    print(f"[✘] {fhir_type} {doc_id} : {exc}")


async def update_patient_ids_from_usernames(db: AsyncIOMotorDatabase) -> None:
    patient_col = db["patients_basic"]
    secondary_cols: List[str] = [
        c for c in RESOURCE_COLLECTIONS.keys() if c != "patients_basic"
    ]

    async with httpx.AsyncClient(timeout=8) as cli:
        async for patient in patient_col.find({"username": {"$exists": True}}):
            username = patient["username"]
            try:
                r = await cli.get(
                    f"{FHIR_SERVER_URL}/Patient",
                    params={"identifier": f"{USERNAME_SYSTEM}|{username}"},
                    headers={"Accept": "application/fhir+json"}
                )
                r.raise_for_status()
                entry = (r.json().get("entry") or [])[0]
                fhir_id = entry["resource"]["id"]

                await patient_col.update_one({"_id": patient["_id"]},
                                             {"$set": {"patient_id": fhir_id}})
                for c in secondary_cols:
                    await db[c].update_many({"username": username},
                                            {"$set": {"patient_id": fhir_id}})

                print(f" patient_id for {username} → {fhir_id}")
            except Exception as e:
                print(f"patient_id refresh for {username} failed: {e}")


async def periodic_sync(db: AsyncIOMotorDatabase):
    print("[🔄] background FHIR sync")
    await ensure_fhir_sync(db)
    await update_patient_ids_from_usernames(db)


def start_scheduler(db: AsyncIOMotorDatabase):
    from apscheduler.schedulers.asyncio import AsyncIOScheduler
    sched = AsyncIOScheduler()
    sched.add_job(lambda: asyncio.create_task(periodic_sync(db)),
                  trigger="interval", minutes=2, id="fhir_resync_job")
    sched.start()
