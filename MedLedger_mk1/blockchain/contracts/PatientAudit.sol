// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract PatientAudit {
    // Event to log stored record hashes along with sender and timestamp
    event RecordStored(address indexed sender, bytes32 recordHash, uint256 timestamp);

    // Function to store the record hash by emitting an event
    function storeRecord(bytes32 recordHash) public {
        emit RecordStored(msg.sender, recordHash, block.timestamp);
    }
}
