import asyncio, os
from motor.motor_asyncio import AsyncIOMotorClient
from sync_fhir import wait_for_fhir_server, ensure_fhir_sync, update_patient_ids_from_usernames

async def run():
    mongo = AsyncIOMotorClient(os.getenv("MONGO_URI", "mongodb://localhost:27017"))
    db    = mongo[os.getenv("MONGO_DB", "medledger_analytics")]

    base  = os.getenv("FHIR_SERVER_URL", "http://localhost:8080/fhir")
    ok    = await wait_for_fhir_server(base)
    if not ok:
        print("FHIR unavailable; aborting")
        return

    print("Manual sync starting…")
    await ensure_fhir_sync(db)
    await update_patient_ids_from_usernames(db)
    print(" Manual sync done.")
    mongo.close()

if __name__ == "__main__":
    asyncio.run(run())
