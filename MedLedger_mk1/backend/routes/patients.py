# backend/routes/patients.py
import asyncio
import traceback

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
import httpx
import config
from pydantic import BaseModel, Field
from auth import get_current_user
from fastapi.responses import StreamingResponse

from utils.pdf_report import generate_patient_pdf
# from mirror_utils import mirror_fetch_resources
from blockchain import store_patient_record
from models import PatientCreate, PatientAdditional, Patient
from routes.users import fake_users_db
from database import get_collection
from datetime import datetime, date, timezone
from typing import List, Dict
from routes.anomaly import ingest_vitals, VitalIn   # adjust imports to your layout
from mongo_client import get_mongo_collection
from routes.mirror_utils import mirror_patient
from crypto import encrypt_text  # your existing RSA encrypt
from datetime import datetime
from fastapi.responses import Response
from utils.pdf_report import render_patient_pdf

# Use the same USERNAME_SYSTEM constant from your create endpoint
USERNAME_SYSTEM = "http://medledger.example.org/username"

router = APIRouter()


@router.get("/me")
async def get_my_patient(current_user: dict = Depends(get_current_user)):
    """
    Fetch the Patient resource for the logged‑in patient via identifier search,
    and return only the fields the UI needs.
    """
    # if current_user["role"] != "patient":
    #     raise HTTPException(status_code=403, detail="Not permitted")

    username = current_user["username"]
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{config.FHIR_SERVER_URL}/Patient",
            params={"identifier": f"{USERNAME_SYSTEM}|{username}"},
            headers={"Accept": "application/fhir+json"}
        )

    if resp.status_code != 200:
        raise HTTPException(
            status_code=500,
            detail=f"FHIR lookup failed: {resp.status_code} {resp.text}"
        )

    bundle = resp.json()
    entries = bundle.get("entry", [])
    if not entries:
        raise HTTPException(status_code=404, detail="Patient record not found")

    resource = entries[0]["resource"]
    # Build a simple dict with exactly the fields we need:
    return {
        "id":        resource.get("id"),
        "name":      resource.get("name"),
        "birthDate": resource.get("birthDate"),
        "gender":    resource.get("gender"),
        "address":   resource.get("address"),   # list of FHIR Address
        "telecom":   resource.get("telecom"),   # list of FHIR ContactPoint
        "contact":   resource.get("contact"),   # list of FHIR Contact
    }



@router.get("/{patient_id}")
async def get_patient_resource(patient_id: str, current_user=Depends(get_current_user)):
    if current_user["role"] not in ("admin", "doctor"):
        raise HTTPException(403, "Not permitted")
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{config.FHIR_SERVER_URL}/Patient/{patient_id}",
            headers={"Accept": "application/fhir+json"}
        )
    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code, detail=resp.text)
    return resp.json()



@router.put("/additional/{patient_id}")
async def add_additional_details(
    patient_id: str,
    details: PatientAdditional,
    current_user=Depends(get_current_user),
    collection = Depends(get_mongo_collection("patients_basic"))  # 👈 Mongo collection
):
    if current_user["role"] != "admin":
        raise HTTPException(403, "Not permitted")

    # 1) fetch current FHIR resource
    async with httpx.AsyncClient() as client:
        get_resp = await client.get(
            f"{config.FHIR_SERVER_URL}/Patient/{patient_id}",
            headers={"Accept": "application/fhir+json"}
        )
    if get_resp.status_code != 200:
        raise HTTPException(
            status_code=get_resp.status_code,
            detail=f"Failed to fetch patient: {get_resp.text}"
        )
    resource = get_resp.json()

    # 2) merge in the new fields
    if details.gender is not None:
        resource["gender"] = details.gender

    # telecom: strip old phone/email then re‑append if provided
    telecom = [t for t in resource.get("telecom", []) if t.get("system") not in ("phone","email")]
    if details.phone:
        telecom.append({"system": "phone", "value": details.phone})
    if details.email:
        telecom.append({"system": "email", "value": details.email})
    if telecom:
        resource["telecom"] = telecom

    # address
    if details.address:
        resource["address"] = [{"text": details.address}]

    # emergency contact: strip old emergency, then re‑append
    contacts = [c for c in resource.get("contact", [])
                if c.get("relationship", [{}])[0].get("text") != "emergency"]
    if details.emergencyContactName or details.emergencyContactPhone:
        em = {
          "relationship": [{"text": "emergency"}],
          "name": {"text": details.emergencyContactName or ""},
          "telecom": []
        }
        if details.emergencyContactPhone:
            em["telecom"].append({
              "system": "phone",
              "value": details.emergencyContactPhone
            })
        contacts.append(em)
    if contacts:
        resource["contact"] = contacts

    # 3) PUT it back to FHIR
    async with httpx.AsyncClient() as client:
        put_resp = await client.put(
            f"{config.FHIR_SERVER_URL}/Patient/{patient_id}",
            json=resource,
            headers={
              "Content-Type": "application/json",
              "Prefer": "return=representation"
            }
        )
    if put_resp.status_code not in (200, 201):
        raise HTTPException(
            status_code=500,
            detail=f"Failed to update patient: {put_resp.text}"
        )

    # ✅ 4) Update MongoDB record
    try:
        update_fields = {
            "gender": details.gender,
            "email": details.email,
            "phone": details.phone,
            "address": details.address,
            "emergency_contact": {
                "name": details.emergencyContactName,
                "phone": details.emergencyContactPhone
            },
            "last_updated": datetime.utcnow()
        }
        # Remove None values
        update_fields = {k: v for k, v in update_fields.items() if v is not None}

        await collection.update_one(
            {"patient_id": patient_id},
            {"$set": update_fields}
        )
    except Exception as mongo_exc:
        print("⚠️ Mongo update failed:", mongo_exc)

    # 5) blockchain audit
    try:
        rec_str = f"action:additional;id:{patient_id};data:{details.json()}"
        receipt = store_patient_record(rec_str)
        print("🔗 blockchain receipt:", receipt)
    except Exception as ex:
        print("⚠️ blockchain audit failed:", ex)

    return put_resp.json()


@router.get("/me/treatments", response_model=List[Dict])
async def get_my_treatments(current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "patient":
        raise HTTPException(403, "Not permitted")

    username = current_user["username"]
    # 1) Find patient by identifier
    async with httpx.AsyncClient() as client:
        pat = await client.get(
            f"{config.FHIR_SERVER_URL}/Patient",
            params={"identifier": f"{USERNAME_SYSTEM}|{username}"},
            headers={"Accept": "application/fhir+json"}
        )
    pat.raise_for_status()
    entries = pat.json().get("entry", [])
    if not entries:
        raise HTTPException(404, "Patient not found")
    patient_id = entries[0]["resource"]["id"]

    # 2) Fetch their MedicationRequest (treatments), sorted newest first
    async with httpx.AsyncClient() as client:
        trt = await client.get(
            f"{config.FHIR_SERVER_URL}/MedicationRequest",
            params={"subject": f"Patient/{patient_id}", "_sort": "-authoredon"},
            headers={"Accept": "application/fhir+json"}
        )
    trt.raise_for_status()

    # 3) Build simple list
    result = []
    for e in trt.json().get("entry", []):
        t = e["resource"]
        result.append({
            "id": t["id"],
            "date": t.get("authoredOn"),
            "medication": t.get("medicationCodeableConcept", {}).get("text")
        })
    return result

@router.get("/me/observations", response_model=List[Dict])
async def get_my_observations(current_user: dict = Depends(get_current_user)):
    """
    Return all Observations (date + note) that doctors have recorded
    for the logged‑in patient, sorted newest first.
    """
    if current_user["role"] != "patient":
        raise HTTPException(403, "Not permitted")

    # 1) Look up the Patient resource by identifier=username
    username = current_user["username"]
    async with httpx.AsyncClient() as client:
        pat_resp = await client.get(
            f"{config.FHIR_SERVER_URL}/Patient",
            params={"identifier": f"{USERNAME_SYSTEM}|{username}"},
            headers={"Accept": "application/fhir+json"}
        )
    if pat_resp.status_code != 200:
        raise HTTPException(500, f"FHIR lookup failed: {pat_resp.status_code} {pat_resp.text}")

    pat_data = pat_resp.json()
    entries = pat_data.get("entry") or []
    if not entries:
        raise HTTPException(404, "Patient record not found")

    patient_id = entries[0]["resource"]["id"]

    # 2) Query Observations for that patient
    async with httpx.AsyncClient() as client:
        obs_resp = await client.get(
            f"{config.FHIR_SERVER_URL}/Observation",
            params={"subject": f"Patient/{patient_id}"},
            headers={"Accept": "application/fhir+json"}
        )
    if obs_resp.status_code != 200:
        raise HTTPException(500, f"FHIR observations fetch failed: {obs_resp.status_code} {obs_resp.text}")

    obs_bundle = obs_resp.json()
    result = []
    for entry in obs_bundle.get("entry", []):
        o = entry["resource"]
        result.append({
            "id": o.get("id"),
            "date": o.get("effectiveDateTime"),
            "note": o.get("valueString")
        })

    # 3) Sort newest first
    result.sort(key=lambda r: r["date"] or "", reverse=True)
    return result


@router.get("/{patient_id}")
async def get_patient_by_id(
    patient_id: str,
    current_user: dict = Depends(get_current_user),
):
    if current_user["role"] not in ("admin", "doctor"):
        raise HTTPException(403, "Not permitted")

    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{config.FHIR_SERVER_URL}/Patient/{patient_id}",
            headers={"Accept": "application/fhir+json"}
        )

    if resp.status_code != 200:
        raise HTTPException(
            status_code=resp.status_code,
            detail=f"FHIR lookup failed: {resp.text}"
        )

    return resp.json()



@router.get("/{patient_id}", summary="Get one patient by ID")
async def get_patient(patient_id: str, current_user=Depends(get_current_user)):
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{config.FHIR_SERVER_URL}/Patient/{patient_id}",
            headers={"Accept": "application/fhir+json"}
        )
    if resp.status_code != 200:
        raise HTTPException(resp.status_code, resp.text)
    return resp.json()

@router.post("/create")
async def create_patient(patient: Patient):
    name_parts = patient.name.split()
    if len(name_parts) >= 2:
        family_name = name_parts[-1]
        given_names = name_parts[:-1]
    else:
        family_name = patient.name
        given_names = [patient.name]

    fhir_payload = {
        "resourceType": "Patient",
        "name": [{
            "family": family_name,
            "given": given_names
        }],
        "birthDate": patient.birthDate
    }

    headers = {
        "Content-Type": "application/json",
        "Prefer": "return=representation"
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{config.FHIR_SERVER_URL}/Patient",
            json=fhir_payload,
            headers=headers
        )

    if response.status_code not in (200, 201):
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create patient on FHIR server: {response.text}"
        )

    patient_id = None
    response_text = response.text.strip()
    if response_text:
        try:
            data = response.json()
            if data.get("resourceType") == "Patient":
                patient_id = data.get("id")
            elif data.get("resourceType") == "Bundle" and "entry" in data:
                entries = data.get("entry")
                if entries and isinstance(entries, list) and len(entries) > 0:
                    patient_id = entries[0].get("resource", {}).get("id")
        except Exception:
            pass

    if not patient_id and "Location" in response.headers:
        location = response.headers["Location"]
        patient_id = location.rstrip("/").split("/")[-1]

    if not patient_id:
        async with httpx.AsyncClient() as client:
            get_response = await client.get(
                f"{config.FHIR_SERVER_URL}/Patient?name={family_name}",
                headers={"Accept": "application/fhir+json"}
            )
        if get_response.status_code in (200, 201):
            try:
                data = get_response.json()
                if data.get("resourceType") == "Bundle" and "entry" in data and len(data["entry"]) > 0:
                    patient_id = data["entry"][0].get("resource", {}).get("id")
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Failed to parse fallback search: {e}")
        else:
            raise HTTPException(status_code=500, detail="Fallback search for patient failed.")

    # --- Blockchain Audit Integration ---
    try:
        patient_data_str = f"action:create;id:{patient_id};name:{patient.name}"
        print("✅ About to call store_patient_record()")
        receipt = store_patient_record(patient_data_str)
        print("✅ Blockchain transaction receipt:", receipt)
    except Exception as e:
        print("❌ Blockchain transaction failed:", e)
        print(traceback.format_exc())
    # --- End Blockchain Integration ---

    return {"message": "Patient created successfully", "id": patient_id}
@router.put("/update/{patient_id}")
async def update_patient(
    patient_id: str,
    updated_data: dict,
    current_user: dict = Depends(get_current_user)
):
    """
    Updates a Patient resource on the FHIR server.
    - Only users in role 'doctor' or 'admin' may call this.
    - Any FHIR Patient fields may be updated, including:
        gender, telecom (phone/email), address, contact, etc.
    - Preserves your blockchain‐audit integration and existing fallbacks.
    """

    # 1) Authorization
    if current_user["role"] not in ("doctor", "admin"):
        raise HTTPException(status_code=403, detail="Not permitted")

    # 2) Ensure the payload is a Patient with the correct ID
    updated_data.setdefault("resourceType", "Patient")
    updated_data["id"] = patient_id

    headers = {
        "Content-Type": "application/json",
        "Prefer": "return=representation"
    }

    # 3) Send the update to HAPI FHIR
    async with httpx.AsyncClient() as client:
        response = await client.put(
            f"{config.FHIR_SERVER_URL}/Patient/{patient_id}",
            json=updated_data,
            headers=headers
        )

    if response.status_code not in (200, 201):
        # Surface any diagnostic HTML/JSON from HAPI
        raise HTTPException(
            status_code=500,
            detail=f"Failed to update patient on FHIR server: {response.text}"
        )

    # 4) Parse the returned Patient (with full representation)
    try:
        data = response.json()
        updated_id = data.get("id")
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to parse update response JSON: {e}"
        )

    # 5) Blockchain audit: record that update
    try:
        audit_str = f"action:update;id:{patient_id};data:{updated_data}"
        receipt = store_patient_record(audit_str)
        print("Blockchain update receipt:", receipt)
    except Exception as e:
        # we do not fail the whole operation if blockchain fails
        print("Blockchain update failed:", e)

    # 6) Return success
    return {"message": "Patient updated successfully", "id": updated_id}

@router.delete("/delete/{patient_id}")
async def delete_patient(patient_id: str, current_user=Depends(get_current_user)):
    """
    Deletes a patient resource from the FHIR server.
    """
    # Access control: only admins
    if current_user["role"] != "admin":
        raise HTTPException(403, "Not permitted")

    async with httpx.AsyncClient() as client:
        response = await client.delete(f"{config.FHIR_SERVER_URL}/Patient/{patient_id}")
    if response.status_code not in (200, 204):
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete patient on FHIR server: {response.text}"
        )

    # --- Blockchain Audit Integration for Delete ---
    try:
        delete_data_str = f"action:delete;id:{patient_id}"
        blockchain_receipt = await store_patient_record(delete_data_str)
        print("Blockchain delete transaction receipt:", blockchain_receipt)
    except Exception as e:
        print("Blockchain delete transaction failed:", e)
    # --- End of Blockchain Integration for Delete ---

    return {"message": "Patient deleted successfully", "id": patient_id}


@router.get("/")
async def list_patients(current_user: dict = Depends(get_current_user)):
    """
    Return all Patient resources as a JSON array under "patients".
    Only admins may call this.
    """
    if current_user["role"] != "admin":
        raise HTTPException(403, "Not permitted")

    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{config.FHIR_SERVER_URL}/Patient?_count=100",
            headers={"Accept": "application/fhir+json"}
        )

    if resp.status_code not in (200, 201):
        raise HTTPException(500, f"FHIR search failed: {resp.status_code} {resp.text}")

    data = resp.json()
    if data.get("resourceType") == "Bundle" and data.get("entry"):
        patients = [entry["resource"] for entry in data["entry"]]
    else:
        patients = []

    return {"patients": patients}

@router.get("/me/allergies", response_model=List[Dict])
async def get_my_allergies(current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "patient":
        raise HTTPException(403, "Not permitted")

    username = current_user["username"]

    try:
        # 1) Lookup the patient by identifier
        async with httpx.AsyncClient() as client:
            pat_resp = await client.get(
                f"{config.FHIR_SERVER_URL}/Patient",
                params={"identifier": f"{USERNAME_SYSTEM}|{username}"},
                headers={"Accept": "application/fhir+json"}
            )
        pat_resp.raise_for_status()
        entries = pat_resp.json().get("entry", [])
        if not entries:
            raise HTTPException(404, "Patient record not found")
        patient_id = entries[0]["resource"]["id"]

        # 2) Fetch AllergyIntolerance for that patient
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{config.FHIR_SERVER_URL}/AllergyIntolerance",
                params={"patient": f"Patient/{patient_id}"},
                headers={"Accept": "application/fhir+json"}
            )
        resp.raise_for_status()
        bundle = resp.json()

        # ✅ If FHIR succeeded, process normally
        result = []
        for entry in bundle.get("entry", []):
            r = entry["resource"]
            result.append({
                "id":   r["id"],
                "date": r.get("recordedDate"),
                "text": r.get("code", {}).get("text")
            })
        result.sort(key=lambda x: x["date"] or "", reverse=True)
        return result

    except Exception as e:
        # ⚠ If FHIR fails, fallback to Mongo mirror
        print(f"[⚠] FHIR allergy fetch failed – using Mongo: {e}")
        patient_id = patient_id if 'patient_id' in locals() else None
        if not patient_id:
            # if lookup patient itself failed
            db = await get_mongo_db()
            patient_doc = await db["patients_basic"].find_one({"username": username})
            if not patient_doc:
                raise HTTPException(404, "Patient not found in database")
            patient_id = patient_doc.get("patient_id")
            if not patient_id:
                raise HTTPException(404, "Patient ID missing in database")

        return await mirror_fetch_resources("AllergyIntolerance", patient_id)

@router.get("/me/conditions", response_model=List[Dict])
async def get_my_conditions(current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "patient":
        raise HTTPException(403, "Not permitted")

    # 1) Lookup patient ID via identifier
    username = current_user["username"]
    async with httpx.AsyncClient() as client:
        pat_resp = await client.get(
            f"{config.FHIR_SERVER_URL}/Patient",
            params={"identifier": f"{USERNAME_SYSTEM}|{username}"},
            headers={"Accept": "application/fhir+json"}
        )
    pat_resp.raise_for_status()
    entries = pat_resp.json().get("entry", [])
    if not entries:
        raise HTTPException(404, "Patient record not found")
    patient_id = entries[0]["resource"]["id"]

    # 2) Fetch all Condition resources
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{config.FHIR_SERVER_URL}/Condition",
            params={"patient": f"Patient/{patient_id}"},
            headers={"Accept": "application/fhir+json"}
        )
    resp.raise_for_status()
    bundle = resp.json()

    # 3) Extract minimal fields and sort newest first
    result = []
    for entry in bundle.get("entry", []):
        r = entry["resource"]
        result.append({
            "id":   r["id"],
            "date": r.get("onsetDateTime"),
            "text": r.get("code", {}).get("text")
        })
    result.sort(key=lambda x: x["date"] or "", reverse=True)
    return result

@router.get("/me/immunizations", response_model=List[Dict])
async def get_my_immunizations(current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "patient":
        raise HTTPException(403, "Not permitted")

    # 1) Lookup patient ID via identifier
    username = current_user["username"]
    async with httpx.AsyncClient() as client:
        pat_resp = await client.get(
            f"{config.FHIR_SERVER_URL}/Patient",
            params={"identifier": f"{USERNAME_SYSTEM}|{username}"},
            headers={"Accept": "application/fhir+json"}
        )
    pat_resp.raise_for_status()
    entries = pat_resp.json().get("entry", [])
    if not entries:
        raise HTTPException(404, "Patient record not found")
    patient_id = entries[0]["resource"]["id"]

    # 2) Fetch all Immunization resources
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{config.FHIR_SERVER_URL}/Immunization",
            params={"patient": f"Patient/{patient_id}"},
            headers={"Accept": "application/fhir+json"}
        )
    resp.raise_for_status()
    bundle = resp.json()

    # 3) Extract minimal fields and sort newest first
    result = []
    for entry in bundle.get("entry", []):
        r = entry["resource"]
        result.append({
            "id":   r["id"],
            "date": r.get("occurrenceDateTime"),
            "text": r.get("vaccineCode", {}).get("text")
        })
    result.sort(key=lambda x: x["date"] or "", reverse=True)
    return result


class VitalPublic(BaseModel):
    patient_id: str = Field(..., description="FHIR Patient.id")
    spo2: float     = Field(..., ge=0, le=100)
    temperature: float = Field(..., description="°C")
    heart_rate: float  = Field(..., description="bpm")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

@router.post("/vitals/public", summary="Public ingest of vitals (no JWT)")
async def vitals_public(
    vp: VitalPublic,
    bg: BackgroundTasks
):
    """
    Ingest vitals for vp.patient_id without any authentication.
    """

    # ---------- FIX BEGINS ----------
    v = VitalIn(
        patient_id = vp.patient_id,          # <-- ADD THIS LINE
        spo2       = vp.spo2,
        temperature= vp.temperature,
        heart_rate = vp.heart_rate,
        timestamp  = vp.timestamp
    )
    # ----------  FIX ENDS   ----------

    fake_user = {"role": "patient", "username": vp.patient_id}
    return await ingest_vitals(v, bg, fake_user)

@router.get("/me/report")
async def download_my_report(current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "patient":
        raise HTTPException(403, "Not permitted")

    username = current_user["username"]

    # 1) Lookup the Patient by username
    async with httpx.AsyncClient() as client:
        pat_resp = await client.get(
            f"{config.FHIR_SERVER_URL}/Patient",
            params={"identifier": f"{USERNAME_SYSTEM}|{username}"},
            headers={"Accept": "application/fhir+json"}
        )
    pat_resp.raise_for_status()
    entries = pat_resp.json().get("entry", [])
    if not entries:
        raise HTTPException(404, "Patient record not found")
    patient = entries[0]["resource"]
    patient_id = patient["id"]

    # 2) Pull clinical data
    async with httpx.AsyncClient() as client:
        def fhir_fetch(resource, params):
            return client.get(
                f"{config.FHIR_SERVER_URL}/{resource}",
                params=params,
                headers={"Accept": "application/fhir+json"}
            )

        resps = await asyncio.gather(
            fhir_fetch("Observation", {"subject": f"Patient/{patient_id}", "_sort": "-date"}),
            fhir_fetch("AllergyIntolerance", {"patient": f"Patient/{patient_id}"}),
            fhir_fetch("Condition", {"patient": f"Patient/{patient_id}"}),
            fhir_fetch("MedicationRequest", {"subject": f"Patient/{patient_id}"}),
            fhir_fetch("Immunization", {"patient": f"Patient/{patient_id}"}),
            return_exceptions=True
        )

    # Process fetched responses
    observations = []
    allergies = []
    conditions = []
    treatments = []
    immunizations = []

    keys = [observations, allergies, conditions, treatments, immunizations]
    for i, r in enumerate(resps):
        if isinstance(r, Exception):
            print(f"[⚠] FHIR fetch error: {r}")
            continue
        if r.status_code == 200:
            bundle = r.json()
            entries = bundle.get("entry", [])
            resources = [e["resource"] for e in entries]
            keys[i].extend(resources)

    # 3) Generate PDF
    pdf_bytes = await generate_patient_pdf({
        "patient": patient,
        "observations": observations,
        "allergies": allergies,
        "conditions": conditions,
        "treatments": treatments,
        "immunizations": immunizations
    })

    return StreamingResponse(
        pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=patient_report.pdf"}
    )
