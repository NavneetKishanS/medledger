
import httpx
from typing import List, Dict
from config import FHIR_SERVER_URL


async def fetch_fhir_resources(kind: str, params: Dict[str, str]) -> List[Dict]:
    """
    GET [FHIR_SERVER_URL]/<kind>?<params>
    Returns the list of resources from Bundle.entry[].resource
    """
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{FHIR_SERVER_URL}/{kind}",
            params=params,
            headers={"Accept": "application/fhir+json"}
        )
    resp.raise_for_status()
    bundle = resp.json()
    entries = bundle.get("entry", [])
    return [e["resource"] for e in entries if "resource" in e]


async def create_fhir_resource(kind: str, resource_body: Dict) -> Dict:
    """
    POST [FHIR_SERVER_URL]/<kind>
    with JSON body = a FHIR resource
    Returns the created resource (as returned by HAPI)
    """
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{FHIR_SERVER_URL}/{kind}",
            json=resource_body,
            headers={"Content-Type": "application/fhir+json"}
        )
    resp.raise_for_status()
    return resp.json()
