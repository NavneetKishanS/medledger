// Import ethers from Hardhat
const { ethers } = require("hardhat");

async function main() {
  console.log("Deploying contract using manual transaction...");

  // Retrieve the ContractFactory for PatientAudit
  const PatientAudit = await ethers.getContractFactory("PatientAudit");
  console.log("Contract factory obtained:", PatientAudit ? "Yes" : "No");

  // Get the default signer (first account)
  const signer = (await ethers.getSigners())[0];

  // Connect the factory to the signer
  const factoryWithSigner = PatientAudit.connect(signer);

  // Get the raw deployment transaction data
  let deployTxData = factoryWithSigner.getDeployTransaction();

  // If the deployment data is missing, fill it using the factory's bytecode
  if (!deployTxData.data) {
    console.log("Deployment transaction data missing; setting it using the factory's bytecode.");
    deployTxData.data = PatientAudit.bytecode;
  }

  // Set a gas limit for the transaction (adjust as needed)
  deployTxData.gasLimit = 5000000;

  // Manually send the transaction, ensuring the "from" field is set
  const txResponse = await signer.sendTransaction({
    ...deployTxData,
    from: signer.address,
  });
  console.log("Deployment transaction hash:", txResponse.hash);

  // Wait for the transaction receipt
  const receipt = await txResponse.wait();
  console.log("Full receipt:", receipt);
  console.log("PatientAudit deployed to:", receipt.contractAddress, "in block:", receipt.blockNumber);

  // Attach the deployed contract instance so you can interact with it
  const deployedContract = PatientAudit.attach(receipt.contractAddress);
  // In ethers v6, use getAddress() to get the contract's address
  const deployedContractAddress = await deployedContract.getAddress();
  console.log("Contract instance ready at address:", deployedContractAddress);
}

main()
  .then(() => process.exit(0))
  .catch((error) => {
    console.error("Deployment error:", error);
    process.exit(1);
  });
