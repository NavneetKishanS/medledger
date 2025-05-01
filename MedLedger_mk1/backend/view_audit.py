from blockchain import contract, w3
import json

START_BLOCK = 0

event_sig = w3.keccak(text="RecordStored(address,bytes32,uint256)").hex()

logs = w3.eth.get_logs({
    "fromBlock": START_BLOCK,
    "toBlock": "latest",
    "address": contract.address,
    "topics": [event_sig]
})

if not logs:
    print("No audit events found. Make sure you’ve actually called storeRecord().")
else:
    print(f"Found {len(logs)} RecordStored events:\n")
    for raw in logs:
        evt = contract.events.RecordStored().process_log(raw)
        print(json.dumps({
            "transactionHash": evt.transactionHash.hex(),
            "blockNumber": evt.blockNumber,
            "sender": evt.args.sender,
            "recordHash": evt.args.recordHash.hex(),
            "timestamp": evt.args.timestamp
        }, indent=2))
