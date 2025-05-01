

# MedLedger: Secure Health Records System based on APIs

MedLedger is a secure healthcare records system designed to address challenges in managing critical health data across multiple systems. It leverages HL7 FHIR standards to ensure interoperability, uses JWT-based authentication for secure access, and integrates a blockchain audit layer for immutable record-keeping. A React-based frontend provides role-based dashboards for patients, doctors, and administrators.

---

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Architecture & Project Structure](#architecture--project-structure)
- [Setup & Installation](#setup--installation)
  - [Backend](#backend)
  - [Frontend](#frontend)
  - [Blockchain Layer](#blockchain-layer)
- [Running the Project](#running-the-project)
- [Testing the Project](#testing-the-project)
  - [Backend Testing](#backend-testing)
  - [Blockchain Testing & Viewing the Audit Trail](#blockchain-testing--viewing-the-audit-trail)
  - [Frontend Testing](#frontend-testing)
- [Leveraging the Blockchain Audit Trail](#leveraging-the-blockchain-audit-trail)
- [Future Enhancements](#future-enhancements)
- [License](#license)

---

## Overview

MedLedger addresses challenges such as unauthorized access, inefficient data handling, and lack of transparency in healthcare systems. It combines:

- A **FastAPI** backend that implements CRUD operations for patient data and communicates with a **HAPI FHIR server**.
- **JWT authentication** for secure, role-based access.
- A **blockchain audit layer** that records immutable cryptographic hashes of patient data modifications on a local Hardhat network.
- A **React frontend** providing separate dashboards for patients, doctors, and administrators.

---

## Features


- **FHIR-Compliant Data Management:**  
  Patient data is stored and managed through a HAPI FHIR server.

- **JWT-Based Security:**  
  Secure endpoints with JWT tokens ensuring role-based access control.

- **Blockchain Audit Trail:**  
  A Solidity smart contract logs an immutable audit trail for all critical patient data operations.

- **Role-Based React Frontend:**  
  Separate interfaces for patients (read-only), doctors (view/update), and administrators (full CRUD).

---

## Architecture & Project Structure

The project is divided into two main parts:

### Backend (FastAPI + HAPI FHIR + Blockchain Audit Layer)

```
project-root/
└── backend/
    ├── __init__.py              
    ├── app.py                   # FastAPI application; routes and middleware configuration
    ├── config.py                # Environment configuration (FHIR URL, JWT secret, blockchain settings, etc.)
    ├── auth.py                  # JWT token generation and verification helpers
    ├── models.py                # Pydantic models (Patient, UserLogin, etc.)
    ├── routes/
    │   ├── __init__.py          
    │   ├── patients.py          # Patient CRUD endpoints (create, update, delete, etc.)
    │   └── users.py             # User login endpoint
    ├── blockchain.py            # Blockchain integration module (Web3.py functions to log audit trail)
    ├── requirements.txt         # Python dependencies
    └── .env                     # Environment variables
```

### Frontend (React)

```
project-root/
└── fhir-frontend/
    ├── node_modules/
    ├── public/
    ├── src/
    │   ├── components/
    │   │   ├── AuthContext.js   
    │   │   ├── PrivateRoute.js  
    │   │   ├── NavBar.js        
    │   │   └── NavBar.css       
    │   ├── pages/
    │   │   ├── Login.js         
    │   │   ├── PatientDashboard.js  
    │   │   ├── DoctorDashboard.js   
    │   │   └── AdminDashboard.js    
    │   ├── App.js               
    │   ├── index.js             
    │   └── setupProxy.js        
    ├── package.json             
    └── README.md                
```

### Blockchain Layer (Hardhat)

```
project-root/
└── blockchain/
    ├── contracts/
    │   └── PatientAudit.sol   # Solidity smart contract for audit logging
    ├── scripts/
    │   └── deploy.js          # Deployment script for PatientAudit.sol
    ├── artifacts/             # Hardhat compilation output (includes PatientAudit.json)
    └── package.json           # Node dependencies for Hardhat
```

---

## Setup & Installation

### Backend

1. **Navigate to the backend folder:**

   ```bash
   cd project-root/backend
   ```

2. **Create a virtual environment and activate it:**

   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows use: venv\Scripts\activate
   ```

3. **Install Python dependencies:**

   ```bash
   pip install -r requirements.txt
   ```

4. **Configure Environment Variables:**

   Create or update your `.env` file with values similar to:

   ```
   MONGO_URI=mongodb://localhost:27017
   FHIR_SERVER_URL=http://localhost:8080/fhir
   JWT_SECRET_KEY=supersecretkey

   # Blockchain settings:
   BLOCKCHAIN_NODE_URL=http://127.0.0.1:8545
   CONTRACT_ADDRESS=0x5FC8d32690cc91D4c39d9d3abcBD16989F875707
   PRIVATE_KEY=<YOUR_PRIVATE_KEY_FROM_HARDHAT_NODE>
   ```

   Replace `<YOUR_PRIVATE_KEY_FROM_HARDHAT_NODE>` with one of the private keys shown when you start the Hardhat node.

5. **Start the HAPI FHIR Server using Docker:**

   ```bash
   docker pull hapiproject/hapi:latest
   docker run -d --name hapi-fhir -p 8080:8080 hapiproject/hapi:latest
   ```

### Frontend

1. **Navigate to the frontend folder:**

   ```bash
   cd project-root/fhir-frontend
   ```

2. **Install Node.js dependencies:**

   ```bash
   npm install
   ```

### Blockchain Layer

1. **Navigate to the blockchain folder:**

   ```bash
   cd project-root/blockchain
   ```

2. **Install Node dependencies:**

   ```bash
   npm install
   ```

3. **Compile and Deploy the Smart Contract:**

   - **Start the Hardhat node in one terminal:**

     ```bash
     npx hardhat node
     ```

     *Expected Output:* A list of accounts and their private keys along with network details.

   - **Deploy the Contract in another terminal:**

     ```bash
     npx hardhat run scripts/deploy.js --network localhost
     ```

     *Expected Output:*  
     ```
     Deploying contract using manual transaction...
     Contract factory obtained: Yes
     Deployment transaction hash: 0x... (transaction hash)
     PatientAudit deployed to: 0x... (deployed contract address) in block: <block number>
     Contract instance ready at address: 0x... (same as deployed address)
     ```

---

## Running the Project

1. **Backend:**  
   Ensure your virtual environment is activated and run:

   ```bash
   uvicorn app:app --reload --host 0.0.0.0 --port 5000
   ```

2. **Frontend:**  
   In the `fhir-frontend` folder, run:

   ```bash
   npm start
   ```

3. **Blockchain Layer:**  
   - Keep the Hardhat node running (started earlier).  
   - The smart contract is deployed and its address is stored in your environment variable (`CONTRACT_ADDRESS`).

---

## Testing the Project

### Backend Testing (via cURL)

- **Login:**

  ```bash
  curl -v -X POST "http://localhost:5000/users/login" \
       -H "Content-Type: application/json" \
       -d '{"username": "testuser", "password": "password123"}'
  ```

  *Expected Output:* A JSON object containing a JWT token.

- **Create Patient:**

  ```bash
  curl -v -X POST "http://localhost:5000/patients/create" \
       -H "Content-Type: application/json" \
       -H "Authorization: Bearer <TOKEN>" \
       -d '{"name": "John Doe", "birthDate": "1984-02-20"}'
  ```

  *Expected Output:*  
  ```json
  {"message": "Patient created successfully", "id": "1"}
  ```

- **Update Patient:**

  ```bash
  curl -v -X PUT "http://localhost:5000/patients/update/1" \
       -H "Content-Type: application/json" \
       -H "Authorization: Bearer <TOKEN>" \
       -d '{"resourceType": "Patient", "name": [{"family": "Doe", "given": ["Johnathan"]}], "birthDate": "1984-02-20"}'
  ```

  *Expected Output:*  
  ```json
  {"message": "Patient updated successfully", "id": "1"}
  ```

- **Delete Patient:**

  ```bash
  curl -v -X DELETE "http://localhost:5000/patients/delete/1" \
       -H "Authorization: Bearer <TOKEN>"
  ```

  *Expected Output:*  
  ```json
  {"message": "Patient deleted successfully", "id": "1"}
  ```

### Blockchain Testing & Viewing the Audit Trail

#### Using Hardhat Console

1. **Open the Hardhat Console:**

   ```bash
   npx hardhat console --network localhost
   ```

2. **Attach to Your Deployed Contract:**

   Replace `<DEPLOYED_ADDRESS>` with your contract address (from deployment output):

   ```javascript
   const contract = await ethers.getContractAt("PatientAudit", "<DEPLOYED_ADDRESS>");
   ```

3. **Query for Audit Events:**

   Retrieve all events from block 0 (or from the deployment block):

   ```javascript
   const events = await contract.queryFilter("RecordStored", 0, "latest");
   console.log(events);
   ```

   *Expected Output:* An array of event objects with details such as sender, recordHash, and timestamp.

#### Using a Python Script

Create a file called `view_audit.py` in the backend directory with the following code:

```python
from blockchain import contract, w3
import json

# Set the starting block (use 0 or the block number of deployment)
START_BLOCK = 0

# Create a filter for the RecordStored event
event_filter = contract.events.RecordStored.create_filter(from_block=START_BLOCK, to_block="latest")
events = event_filter.get_all_entries()

if not events:
    print("No audit events found. Ensure that transactions triggering RecordStored have occurred.")
else:
    print("Audit events found:")
    for event in events:
        print(json.dumps(dict(event), indent=2, default=str))
```

Run it with:

```bash
python view_audit.py
```

*Expected Output:* JSON formatted event logs showing the audit trail.

### Frontend Testing

1. **Login:**  
   Navigate to [http://localhost:3000/login](http://localhost:3000/login), enter your credentials, and verify you’re authenticated.

2. **Navigate Dashboards:**  
   - **Patient Dashboard:** [http://localhost:3000/patient](http://localhost:3000/patient)
   - **Doctor Dashboard:** [http://localhost:3000/doctor](http://localhost:3000/doctor)
   - **Admin Dashboard:** [http://localhost:3000/admin](http://localhost:3000/admin)

   *Expected Output:*  
   The dashboards should display patient data, allow updates (for doctors/admins), and list all patients accordingly.

---

## Leveraging the Blockchain Audit Trail

- **Immutable Record Keeping:**  
  The audit trail provides a tamper-proof log of patient record operations, which is invaluable for compliance and forensic analysis.
- **Real-Time Monitoring:**  
  Use event listeners (via the Hardhat console or a backend service) to trigger alerts when critical operations occur.
- **User Verification:**  
  Allow administrators or auditors to verify that patient records have not been tampered with by comparing the on-chain hash with off-chain data.
- **Centralized Reporting:**  
  Integrate blockchain events into your reporting/dashboard tools to provide a holistic view of data integrity across your system.

---

## Future Enhancements

- **Enhanced Security:**  
  Improve key management and consider integrating secure hardware modules for signing transactions.
- **Broader FHIR Integration:**  
  Extend support to additional FHIR resources (e.g., Observations, Conditions).
- **Scalability:**  
  Explore using a testnet or private Ethereum network as you scale, considering gas optimizations and transaction throughput.
- **UI Enhancements:**  
  Enhance the blockchain audit dashboard to provide user-friendly views of on-chain events.

---
