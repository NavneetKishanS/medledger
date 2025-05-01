from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from pymongo.errors import PyMongoError
from database import get_audit_collection  # Assumes you already have this
from bson import json_util
import json

router = APIRouter()


@router.post("/audit/store")
async def store_audit_log(audit_data: dict):
    """
    Store blockchain transaction receipt into MongoDB audit_trail.
    Expected payload is the full dict printed from the store_patient_record() receipt.
    """
    try:
        audit_col = get_audit_collection()
        result = await audit_col.insert_one(audit_data)
        return {"message": "Stored successfully", "inserted_id": str(result.inserted_id)}
    except PyMongoError as e:
        raise HTTPException(status_code=500, detail=f"MongoDB Error: {e}")


@router.get("/audit/logs")
async def get_audit_logs():
    """
    Return all audit records stored in MongoDB audit_trail.
    """
    try:
        audit_col = get_audit_collection()
        cursor = audit_col.find()
        logs = []
        async for doc in cursor:
            logs.append(json.loads(json_util.dumps(doc)))
        return JSONResponse(content=logs)
    except PyMongoError as e:
        raise HTTPException(status_code=500, detail=f"MongoDB Error: {e}")
