# backend/routes/doctor.py
from fastapi import APIRouter, HTTPException, Depends, Query
import httpx, config
from auth import get_current_user
from datetime import datetime, timezone
from fhir_service import fetch_fhir_resources, create_fhir_resource
from typing import List, Dict
from mongo_client import get_mongo_collection
from crypto import decrypt_text, encrypt_text
from fastapi.responses import StreamingResponse
from utils.pdf_report import render_patient_pdf
import io
from config import USERNAME_SYSTEM

router = APIRouter()
FHIR = config.FHIR_SERVER_URL

def check_doctor(user):
    if user["role"] != "doctor":
        raise HTTPException(403, "Not permitted")

@router.get("/patients")
async def list_or_search_patients(
    q: str = Query(None, description="Name fragment or ID to search"),
    user=Depends(get_current_user)
):
    check_doctor(user)
    params = {"_count": 100}
    if q:
        params["name"] = q
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{FHIR}/Patient", params=params,
                                headers={"Accept": "application/fhir+json"})
    if resp.status_code != 200:
        raise HTTPException(500, f"FHIR search failed: {resp.status_code}")
    bundle = resp.json()
    return [e["resource"] for e in bundle.get("entry", [])]

@router.get("/patients/{patient_id}")
async def get_patient(patient_id: str, user=Depends(get_current_user)):
    check_doctor(user)
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{FHIR}/Patient/{patient_id}",
            headers={"Accept": "application/fhir+json"}
        )
    if resp.status_code != 200:
        raise HTTPException(resp.status_code, f"Failed to fetch patient: {resp.text}")
    return resp.json()

# -----------------------------------
# GET all observations by patient_id
# -----------------------------------
@router.get("/observations/{patient_id}", response_model=List[Dict])
async def list_observations(
    patient_id: str,
    user=Depends(get_current_user),
    col=Depends(get_mongo_collection("observations"))
):
    check_doctor(user)

    # Try FHIR first
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(
                f"{FHIR}/Observation",
                params={"subject": f"Patient/{patient_id}", "_sort": "-date"},
                headers={"Accept": "application/fhir+json"}
            )
        resp.raise_for_status()
        bundle = resp.json()
        return [e["resource"] for e in bundle.get("entry", [])]

    except Exception as e:
        print(f"[⚠] FHIR fetch failed: {e}")
        # Fallback to Mongo
        mongo_results = await col.find({"patient_id": patient_id}).sort("timestamp", -1).to_list(length=100)
        observations = [entry.get("payload") for entry in mongo_results if "payload" in entry]

        if not observations:
            raise HTTPException(500, f"No observations found (FHIR and Mongo failed)")
        return observations

# -----------------------------------
# POST a new observation
# -----------------------------------
@router.post("/observations/{patient_id}")
async def create_observation(
    patient_id: str,
    payload: dict,
    user=Depends(get_current_user),
    col=Depends(get_mongo_collection("observations"))
):
    check_doctor(user)
    doctor_username = user["username"]

    # Validate input
    if "text" not in payload or not payload["text"]:
        raise HTTPException(400, detail="Missing 'text' in payload")

    code_text = payload.get("code", {}).get("text", "Note")
    obs_time = datetime.utcnow().replace(tzinfo=timezone.utc)
    encrypted_text = encrypt_text(payload["text"])

    username = None

    # Fetch username from FHIR
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{FHIR}/Patient/{patient_id}",
                headers={"Accept": "application/fhir+json"}
            )
        resp.raise_for_status()
        patient = resp.json()

        identifiers = patient.get("identifier", [])
        username = next(
            (i.get("value") for i in identifiers if i.get("system") == USERNAME_SYSTEM),
            None
        )

        if not username:
            raise HTTPException(400, detail="Username not found in patient's FHIR identifiers")
    except Exception as e:
        raise HTTPException(500, f"Failed to fetch patient username from FHIR: {str(e)}")

    # Build FHIR Observation
    obs = {
        "resourceType": "Observation",
        "status": "final",
        "category": [{
            "coding": [{
                "system": "http://terminology.hl7.org/CodeSystem/observation-category",
                "code": "exam"
            }]
        }],
        "code": payload.get("code", {"text": "Note"}),
        "subject": {"reference": f"Patient/{patient_id}"},
        "effectiveDateTime": obs_time.isoformat(),
        "valueString": payload["text"]
    }

    fhir_id = None
    synced = False
    error = None

    # Post to FHIR
    try:
        async with httpx.AsyncClient() as client:
            post_resp = await client.post(
                f"{FHIR}/Observation",
                json=obs,
                headers={"Content-Type": "application/fhir+json"}
            )
        post_resp.raise_for_status()
        fhir_id = post_resp.json().get("id")
        synced = True
    except Exception as e:
        error = str(e)

    # Save to Mongo
    await col.insert_one({
        "username": username,
        "patient_id": patient_id,
        "doctor_username": doctor_username,
        "timestamp": obs_time,
        "code": code_text,
        "text": encrypted_text,
        "resource_type": "Observation",
        "fhir_id": fhir_id,
        "synced": synced,
        "error": error,
        "payload": obs
    })

    if not synced:
        raise HTTPException(500, f"Failed to post observation to FHIR: {error}")

    return {"message": "Observation recorded", "fhir_id": fhir_id}


# ─────────────────────────────────────────────────────────────────────────────
# GET  /doctor/treatments/{patient_id}
# ─────────────────────────────────────────────────────────────────────────────
@router.get("/treatments/{patient_id}", response_model=List[Dict])
async def list_treatments(
    patient_id: str,
    user = Depends(get_current_user),
    col  = Depends(get_mongo_collection("treatments")),
):
    check_doctor(user)

    # 1️⃣  try FHIR
    try:
        async with httpx.AsyncClient(timeout=5) as cli:
            r = await cli.get(
                f"{FHIR}/MedicationRequest",
                params  = {"subject": f"Patient/{patient_id}", "_sort": "-authoredon"},
                headers = {"Accept": "application/fhir+json"},
            )
        r.raise_for_status()
        bundle = r.json()
        return [e["resource"] for e in bundle.get("entry", [])]

    # 2️⃣  fall back to Mongo mirror
    except Exception as e:
        print(f"[⚠] FHIR MedicationRequest fetch failed → {e}")
        docs = await col.find({"patient_id": patient_id}) \
                        .sort("timestamp", -1) \
                        .to_list(length=100)
        mirrored = [d["payload"] for d in docs if "payload" in d]
        if not mirrored:
            raise HTTPException(500, "No treatments found (FHIR & Mongo failed)")
        return mirrored

# ─────────────────────────────────────────────────────────────────────────────
# POST /doctor/treatments/{patient_id}
# ─────────────────────────────────────────────────────────────────────────────
@router.post("/treatments/{patient_id}")
async def create_treatment(
    patient_id: str,
    body: Dict,
    user = Depends(get_current_user),
    col  = Depends(get_mongo_collection("treatments")),
):
    """
    body = { "medicationText": "Amoxicillin 500 mg TID" }
    """
    check_doctor(user)
    doctor_username = user["username"]

    med_text = body.get("medicationText")
    if not med_text:
        raise HTTPException(400, "medicationText is required")

    # ── resolve the patient’s username (needed for Mongo mirror) ────────────
    try:
        async with httpx.AsyncClient() as cli:
            r = await cli.get(
                f"{FHIR}/Patient/{patient_id}",
                headers={"Accept": "application/fhir+json"},
            )
        r.raise_for_status()
        patient    = r.json()
        username = next(
            (idn["value"] for idn in patient.get("identifier", [])
             if idn.get("system") == USERNAME_SYSTEM),
            None,
        )
        if not username:
            raise RuntimeError("username identifier missing")
    except Exception as e:
        raise HTTPException(500, f"Could not fetch patient username: {e}")

    # ── build FHIR resource ────────────────────────────────────────────────
    authored_on = datetime.utcnow().date().isoformat()
    mr_resource = {
        "resourceType"             : "MedicationRequest",
        "status"                   : "active",
        "intent"                   : "order",
        "subject"                  : {"reference": f"Patient/{patient_id}"},
        "authoredOn"               : authored_on,
        "medicationCodeableConcept": {"text": med_text},
    }

    fhir_id = None
    synced  = False
    error   = None

    # 1️⃣  POST to FHIR
    try:
        async with httpx.AsyncClient() as cli:
            r = await cli.post(
                f"{FHIR}/MedicationRequest",
                json    = mr_resource,
                headers = {"Content-Type": "application/fhir+json"},
            )
        r.raise_for_status()
        fhir_id = r.json().get("id")
        synced  = True
    except Exception as e:
        error = str(e)

    # 2️⃣  Mirror in Mongo   (stored even if FHIR failed)
    await col.insert_one({
        "username"      : username,
        "patient_id"    : patient_id,
        "doctor_username": doctor_username,
        "timestamp"     : datetime.utcnow(),
        "medicationText": med_text,
        "resource_type" : "MedicationRequest",
        "fhir_id"       : fhir_id,
        "synced"        : synced,
        "error"         : error,
        "payload"       : mr_resource,
    })

    if not synced:
        raise HTTPException(500, f"FHIR create failed: {error}")

    return {"message": "Treatment recorded", "fhir_id": fhir_id}

# ---------------------------------------------------------------------------
# Allergies  –  exact same mirroring pattern as Observations
# ---------------------------------------------------------------------------

# 🔎  GET /doctor/allergies/{patient_id}
@router.get("/allergies/{patient_id}", response_model=List[Dict])
async def list_allergies(
    patient_id: str,
    user          = Depends(get_current_user),
    col           = Depends(get_mongo_collection("allergies"))
):
    check_doctor(user)

    # 1️⃣ Try FHIR first ------------------------------------------------------
    try:
        async with httpx.AsyncClient(timeout=5.0) as cli:
            r = await cli.get(
                f"{FHIR}/AllergyIntolerance",
                params = {
                    "patient": f"Patient/{patient_id}",
                    "_sort"  : "-recorded-date"
                },
                headers = {"Accept": "application/fhir+json"}
            )
        r.raise_for_status()
        bundle = r.json()
        return [e["resource"] for e in bundle.get("entry", [])]

    # 2️⃣ Fallback → Mongo ----------------------------------------------------
    except Exception as e:
        print(f"[⚠] FHIR allergy fetch failed – using Mongo: {e}")
        docs = (
            await col.find({"patient_id": patient_id})
                     .sort("timestamp", -1)
                     .to_list(length=100)
        )
        resources = [d.get("payload") for d in docs if "payload" in d]
        if not resources:
            raise HTTPException(500, "No allergies found (FHIR & Mongo both failed)")
        return resources


# ✍️  POST /doctor/allergies/{patient_id}
@router.post("/allergies/{patient_id}")
async def create_allergy(
    patient_id: str,
    body       : Dict,                       # { "text": "Peanuts" }
    user       = Depends(get_current_user),
    col        = Depends(get_mongo_collection("allergies"))
):
    check_doctor(user)
    doctor_username = user["username"]

    # --- sanity --------------------------------------------------------------
    if not body.get("text"):
        raise HTTPException(400, "Missing 'text' field")

    now_iso = datetime.utcnow().replace(tzinfo=timezone.utc).isoformat()

    # Who is this patient’s username?  (same trick the observation route uses)
    try:
        async with httpx.AsyncClient() as cli:
            pat = await cli.get(
                f"{FHIR}/Patient/{patient_id}",
                headers={"Accept": "application/fhir+json"}
            )
        pat.raise_for_status()
        identifiers = pat.json().get("identifier", [])
        username = next(
            (i["value"] for i in identifiers if i.get("system") == USERNAME_SYSTEM),
            None
        )
        if not username:
            raise HTTPException(400, "username identifier missing on Patient")
    except Exception as exc:
        raise HTTPException(500, f"Unable to read Patient/{patient_id}: {exc}")

    # --- build FHIR AllergyIntolerance --------------------------------------
    allergy_res = {
        "resourceType"      : "AllergyIntolerance",
        "patient"           : {"reference": f"Patient/{patient_id}"},
        "clinicalStatus"    : {"coding":[{"system":"http://terminology.hl7.org/CodeSystem/allergyintolerance-clinical",
                                          "code":"active"}]},
        "verificationStatus": {"coding":[{"system":"http://terminology.hl7.org/CodeSystem/allergyintolerance-verification",
                                          "code":"unconfirmed"}]},
        "code"              : {"text": body["text"]},
        "recordedDate"      : now_iso
    }

    fhir_id = None
    synced  = False
    error   = None

    # --- push to FHIR --------------------------------------------------------
    try:
        async with httpx.AsyncClient() as cli:
            r = await cli.post(
                f"{FHIR}/AllergyIntolerance",
                json    = allergy_res,
                headers = {"Content-Type": "application/fhir+json"}
            )
        r.raise_for_status()
        fhir_id = r.json().get("id")
        synced  = True
    except Exception as exc:
        error = str(exc)

    # --- mirror to Mongo -----------------------------------------------------
    await col.insert_one({
        "username"      : username,
        "patient_id"    : patient_id,
        "doctor_username": doctor_username,

        "timestamp"     : datetime.utcnow(),
        "text"          : body["text"],         # 🔓  *plain-text, no RSA*
        "resource_type" : "AllergyIntolerance",
        "fhir_id"       : fhir_id,
        "synced"        : synced,
        "error"         : error,
        "payload"       : allergy_res
    })

    if not synced:
        raise HTTPException(500, f"Failed to post to FHIR: {error}")

    return {"message": "Allergy recorded", "fhir_id": fhir_id}

# ---------------------------------------------------------------------------
# CONDITIONS
# ---------------------------------------------------------------------------

# ─────────────────────────────────────────────────────────────────────────────
# GET  /doctor/conditions/{patient_id}
# ─────────────────────────────────────────────────────────────────────────────
@router.get("/conditions/{patient_id}", response_model=List[Dict])
async def list_conditions(
    patient_id: str,
    user = Depends(get_current_user),
    col  = Depends(get_mongo_collection("conditions")),
):
    check_doctor(user)

    # 1️⃣ FHIR first
    try:
        async with httpx.AsyncClient(timeout=5) as cli:
            r = await cli.get(
                f"{FHIR}/Condition",
                params  = {"patient": f"Patient/{patient_id}", "_sort": "-date"},
                headers = {"Accept": "application/fhir+json"},
            )
        r.raise_for_status()
        bundle = r.json()
        return [e["resource"] for e in bundle.get("entry", [])]

    # 2️⃣ Fallback to Mongo
    except Exception as e:
        print(f"[⚠] FHIR Condition fetch failed → {e}")
        docs = await col.find({"patient_id": patient_id}) \
                        .sort("timestamp", -1) \
                        .to_list(length=100)
        mirrored = [d["payload"] for d in docs if "payload" in d]
        if not mirrored:
            raise HTTPException(500, "No conditions found (FHIR & Mongo failed)")
        return mirrored


# ─────────────────────────────────────────────────────────────────────────────
# POST /doctor/conditions/{patient_id}
# ─────────────────────────────────────────────────────────────────────────────
@router.post("/conditions/{patient_id}")
async def create_condition(
    patient_id: str,
    body: Dict,                    # { "text": "Hypertension" }
    user = Depends(get_current_user),
    col  = Depends(get_mongo_collection("conditions")),
):
    check_doctor(user)
    doctor_username = user["username"]

    cond_text = body.get("text")
    if not cond_text:
        raise HTTPException(400, "text field is required")

    # ── resolve patient username (for Mongo mirror) ─────────────────────────
    try:
        async with httpx.AsyncClient() as cli:
            r = await cli.get(
                f"{FHIR}/Patient/{patient_id}",
                headers={"Accept": "application/fhir+json"},
            )
        r.raise_for_status()
        patient  = r.json()
        username = next(
            (idn["value"] for idn in patient.get("identifier", [])
             if idn.get("system") == USERNAME_SYSTEM),
            None,
        )
        if not username:
            raise RuntimeError("username identifier missing")
    except Exception as e:
        raise HTTPException(500, f"Could not fetch patient username: {e}")

    # ── build FHIR Condition resource ───────────────────────────────────────
    now_iso = datetime.utcnow().isoformat()
    cond_resource = {
        "resourceType"     : "Condition",
        "clinicalStatus"   : {"coding": [{"system": "http://hl7.org/fhir/condition-clinical", "code": "active"}]},
        "verificationStatus": {"coding": [{"system": "http://hl7.org/fhir/condition-ver-status", "code": "unconfirmed"}]},
        "code"             : {"text": cond_text},
        "subject"          : {"reference": f"Patient/{patient_id}"},
        "onsetDateTime"    : now_iso,
    }

    fhir_id = None
    synced  = False
    error   = None

    # 1️⃣ POST to FHIR
    try:
        async with httpx.AsyncClient() as cli:
            r = await cli.post(
                f"{FHIR}/Condition",
                json    = cond_resource,
                headers = {"Content-Type": "application/fhir+json"},
            )
        r.raise_for_status()
        fhir_id = r.json().get("id")
        synced  = True
    except Exception as e:
        error = str(e)

    # 2️⃣ Mirror to Mongo
    await col.insert_one({
        "username"        : username,
        "patient_id"      : patient_id,
        "doctor_username" : doctor_username,
        "timestamp"       : datetime.utcnow(),
        "text"            : cond_text,
        "resource_type"   : "Condition",
        "fhir_id"         : fhir_id,
        "synced"          : synced,
        "error"           : error,
        "payload"         : cond_resource,
    })

    if not synced:
        raise HTTPException(500, f"FHIR create failed: {error}")

    return {"message": "Condition recorded", "fhir_id": fhir_id}


# ─────────────────────────────────────────────────────────────────────────────
# GET  /doctor/immunizations/{patient_id}
# ─────────────────────────────────────────────────────────────────────────────
@router.get("/immunizations/{patient_id}", response_model=List[Dict])
async def list_immunizations(
    patient_id: str,
    user = Depends(get_current_user),
    col  = Depends(get_mongo_collection("immunizations")),
):
    check_doctor(user)

    # 1️⃣ try FHIR
    try:
        async with httpx.AsyncClient(timeout=5) as cli:
            r = await cli.get(
                f"{FHIR}/Immunization",
                params  = {"patient": f"Patient/{patient_id}", "_sort": "-date"},
                headers = {"Accept": "application/fhir+json"},
            )
        r.raise_for_status()
        bundle = r.json()
        return [e["resource"] for e in bundle.get("entry", [])]

    # 2️⃣ fallback to Mongo
    except Exception as e:
        print(f"[⚠] FHIR Immunization fetch failed → {e}")
        docs = await col.find({"patient_id": patient_id}) \
                        .sort("timestamp", -1) \
                        .to_list(length=100)
        mirrored = [d["payload"] for d in docs if "payload" in d]
        if not mirrored:
            raise HTTPException(500, "No immunizations found (FHIR & Mongo failed)")
        return mirrored


# ─────────────────────────────────────────────────────────────────────────────
# POST /doctor/immunizations/{patient_id}
# ─────────────────────────────────────────────────────────────────────────────
@router.post("/immunizations/{patient_id}")
async def create_immunization(
    patient_id: str,
    body: Dict,                    # { "text": "Flu shot" }
    user = Depends(get_current_user),
    col  = Depends(get_mongo_collection("immunizations")),
):
    check_doctor(user)
    doctor_username = user["username"]

    imm_text = body.get("text")
    if not imm_text:
        raise HTTPException(400, "text field is required")

    # ── resolve patient username (for Mongo mirror) ─────────────────────────
    try:
        async with httpx.AsyncClient() as cli:
            r = await cli.get(
                f"{FHIR}/Patient/{patient_id}",
                headers={"Accept": "application/fhir+json"},
            )
        r.raise_for_status()
        patient    = r.json()
        username = next(
            (idn["value"] for idn in patient.get("identifier", [])
             if idn.get("system") == USERNAME_SYSTEM),
            None,
        )
        if not username:
            raise RuntimeError("username identifier missing")
    except Exception as e:
        raise HTTPException(500, f"Could not fetch patient username: {e}")

    # ── build FHIR Immunization resource ────────────────────────────────────
    now_iso = datetime.utcnow().isoformat()
    imm_resource = {
        "resourceType"   : "Immunization",
        "status"         : "completed",
        "vaccineCode"    : {"text": imm_text},
        "patient"        : {"reference": f"Patient/{patient_id}"},
        "occurrenceDateTime": now_iso,
    }

    fhir_id = None
    synced  = False
    error   = None

    # 1️⃣ POST to FHIR
    try:
        async with httpx.AsyncClient() as cli:
            r = await cli.post(
                f"{FHIR}/Immunization",
                json    = imm_resource,
                headers = {"Content-Type": "application/fhir+json"},
            )
        r.raise_for_status()
        fhir_id = r.json().get("id")
        synced  = True
    except Exception as e:
        error = str(e)

    # 2️⃣ Mirror to Mongo (even if FHIR failed)
    await col.insert_one({
        "username"        : username,
        "patient_id"      : patient_id,
        "doctor_username" : doctor_username,
        "timestamp"       : datetime.utcnow(),
        "text"            : imm_text,
        "resource_type"   : "Immunization",
        "fhir_id"         : fhir_id,
        "synced"          : synced,
        "error"           : error,
        "payload"         : imm_resource,
    })

    if not synced:
        raise HTTPException(500, f"FHIR create failed: {error}")

    return {"message": "Immunization recorded", "fhir_id": fhir_id}



@router.post("/test/decrypt")
async def decrypt_sample(payload: dict):
    """
    payload: { "text": "encrypted-hex-value" }
    """
    try:
        decrypted = decrypt_text(payload["text"])
        return {"decrypted_text": decrypted}
    except Exception as e:
        raise HTTPException(400, f"Failed to decrypt: {str(e)}")

@router.get("/patients/{patient_id}/report", response_class=StreamingResponse)
async def download_patient_report(patient_id: str, user=Depends(get_current_user)):
    # check_doctor(user)

    async with httpx.AsyncClient() as client:
        # notice no Patient/ prefix
        p = await client.get(f"{FHIR}/Patient/{patient_id}")
        a = await client.get(f"{FHIR}/AllergyIntolerance", params={"patient": patient_id, "_sort": "-recorded-date"})
        c = await client.get(f"{FHIR}/Condition", params={"patient": patient_id, "_sort": "-onset-date"})
        i = await client.get(f"{FHIR}/Immunization", params={"patient": patient_id})
        t = await client.get(f"{FHIR}/MedicationRequest", params={"subject": f"Patient/{patient_id}"})
        o = await client.get(f"{FHIR}/Observation", params={"subject": f"Patient/{patient_id}"})

    patient = p.json()
    allergies = a.json().get("entry", [])
    conditions = c.json().get("entry", [])
    immunizations = i.json().get("entry", [])
    treatments = t.json().get("entry", [])
    observations = o.json().get("entry", [])

    context = {
        "patient_name": " ".join(patient["name"][0]["given"]) + " " + patient["name"][0]["family"],
        "birth_date": patient.get("birthDate", "Unknown"),
        "allergies": [entry["resource"]["code"]["text"] for entry in allergies] if allergies else [],
        "conditions": [entry["resource"]["code"]["text"] for entry in conditions] if conditions else [],
        "immunizations": [entry["resource"]["vaccineCode"]["text"] for entry in immunizations] if immunizations else [],
        "treatments": [entry["resource"]["medicationCodeableConcept"]["text"] for entry in treatments] if treatments else [],
        "observations": [entry["resource"]["valueString"] for entry in observations] if observations else [],
    }

    pdf_bytes = render_patient_pdf(context)

    return StreamingResponse(io.BytesIO(pdf_bytes), media_type="application/pdf", headers={
        "Content-Disposition": f"attachment; filename=patient_report_{patient_id}.pdf"
    })
