from web3 import Web3
import json
import os
import hashlib
import re
from config import BLOCKCHAIN_NODE_URL, CONTRACT_ADDRESS, PRIVATE_KEY
from database import get_audit_collection
import asyncio

w3 = Web3(Web3.HTTPProvider(BLOCKCHAIN_NODE_URL))
if not w3.is_connected():
    raise Exception("Unable to connect to the blockchain node at " + BLOCKCHAIN_NODE_URL)

abi_path = os.path.join(os.path.dirname(__file__), "PatientAuditABI.json")
with open(abi_path, "r") as f:
    data = json.load(f)
contract_abi = data["abi"]

# Instantiate the contract using the provided address and the ABI array
contract = w3.eth.contract(
    address=w3.to_checksum_address(CONTRACT_ADDRESS),
    abi=contract_abi
)


def is_valid_private_key(key: str) -> bool:
    key = key.strip().replace("\n", "")
    if not key.startswith("0x"):
        key = "0x" + key
    return bool(re.fullmatch(r"0x[0-9a-fA-F]{64}", key))


def compute_patient_hash(patient_data: str) -> bytes:
    """
    Compute a SHA-256 hash of the patient data and convert it to bytes.
    """
    hash_hex = hashlib.sha256(patient_data.encode('utf-8')).hexdigest()
    return bytes.fromhex(hash_hex)


def store_patient_record(patient_data: str):
    record_hash = compute_patient_hash(patient_data)
    sender = w3.eth.accounts[0]

    tx = contract.functions.storeRecord(record_hash).build_transaction({
        'from': sender,
        'nonce': w3.eth.get_transaction_count(sender),
        'gas': 2000000,
        'gasPrice': w3.to_wei('20', 'gwei')
    })

    key = PRIVATE_KEY.strip().replace("\n", "")
    if not key.startswith("0x"):
        key = "0x" + key
    if not is_valid_private_key(key):
        raise ValueError("Invalid PRIVATE_KEY format.")

    signed_tx = w3.eth.account.sign_transaction(tx, private_key=key)
    tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash)

    # ✅ Mirror receipt into MongoDB
    try:
        audit_collection = get_audit_collection()
        loop = asyncio.get_event_loop()
        loop.create_task(audit_collection.insert_one(dict(receipt)))
        print("📦 Blockchain receipt stored in MongoDB.")
    except Exception as e:
        print("⚠️ Failed to store blockchain receipt in MongoDB:", e)

    return receipt
