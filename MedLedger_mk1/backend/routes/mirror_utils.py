# backend/mirror_utils.py
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

# --------------------------------------------------------------------------- #
# Which Mongo collection stores which FHIR resource?
# Feel free to extend this map if you mirror more resources later.
# --------------------------------------------------------------------------- #
COLLECTION_MAP: Dict[str, str] = {
    "Patient":             "patients_basic",
    "Observation":         "observations",
    "AllergyIntolerance":  "allergies",
    "Condition":           "conditions",
    "MedicationRequest":   "treatments",
    "Immunization":        "immunizations",
}

# --------------------------------------------------------------------------- #
# ①  MIRROR a newly-created Patient (you already had this).
# --------------------------------------------------------------------------- #
async def mirror_patient(
    collection,                    # motor collection object
    fhir_payload: dict,
    fhir_id: Optional[str],
    synced: bool,
    error: Optional[str],
) -> None:
    """
    Insert a flattened copy of the Patient resource into Mongo so that the
    rest of the app can query it quickly (and the sync job can replay it).
    """
    identifier = fhir_payload.get("identifier", [{}])[0]
    name       = fhir_payload.get("name", [{}])[0]
    given      = name.get("given", [])

    doc = {
        "patient_id":  fhir_id,
        "username":    identifier.get("value"),
        "first_name":  given[0] if given else None,
        "last_name":   name.get("family"),
        "birthDate":   fhir_payload.get("birthDate"),
        "timestamp":   datetime.now(timezone.utc),
        "synced":      synced,
        "error":       error,
        "resource_type": "Patient",   #  ← critical for sync_fhir.py
        "payload":     fhir_payload,  #  ← always store full payload
    }
    await collection.insert_one(doc)

# --------------------------------------------------------------------------- #
# ②  FETCH mirrored FHIR resources from Mongo (fallback when FHIR is down)
# --------------------------------------------------------------------------- #
async def mirror_fetch_resources(
    resource_type: str,
    patient_id: str,
    db=None,
    limit: int = 200,
) -> List[Dict[str, Any]]:
    """
    Return a list of mirrored resources (most-recent first) for the given
    `patient_id`.  If `db` is None, we create a temporary connection via
    `mongo_client.get_mongo_db()` so the function can be used anywhere.
    """
    # Lazy import to avoid circular-import problems
    if db is None:
        from mongo_client import get_mongo_db   # local import
        db = await get_mongo_db()

    coll_name = COLLECTION_MAP.get(resource_type)
    if coll_name is None:
        raise ValueError(f"No collection mapping for resource '{resource_type}'")

    coll = db[coll_name]
    cursor = (
        coll.find({"patient_id": patient_id})
            .sort("timestamp", -1)
            .limit(limit)
    )
    docs = await cursor.to_list(length=limit)

    # Prefer the exact FHIR payload if stored; fall back to whole doc
    resources = [
        d.get("payload") or d.get("raw") or d
        for d in docs
    ]
    return resources
