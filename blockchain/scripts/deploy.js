/**
 * deploy.js — Deploys ContentVerifier and writes the contract address + ABI
 * to pipeline/contract_config.json so Python can interact with it via web3.py.
 *
 * Usage:
 *   npx hardhat node             # terminal 1 — keep running
 *   npm run deploy               # terminal 2
 */

const hre = require("hardhat");
const fs  = require("fs");
const path = require("path");

async function main() {
  console.log("🚀 Deploying ContentVerifier to local Hardhat network...");

  const [deployer] = await hre.ethers.getSigners();
  console.log(`   Deployer: ${deployer.address}`);

  const ContentVerifier = await hre.ethers.getContractFactory("ContentVerifier");
  const contract = await ContentVerifier.deploy();
  await contract.waitForDeployment();

  const address = await contract.getAddress();
  console.log(`✅ ContentVerifier deployed at: ${address}`);

  // Read ABI from Hardhat's compiled artifact
  const artifactPath = path.join(
    __dirname, "..", "artifacts", "contracts",
    "ContentVerifier.sol", "ContentVerifier.json"
  );
  const artifact = JSON.parse(fs.readFileSync(artifactPath, "utf8"));

  // Write config for Python pipeline
  const config = {
    address:    address,
    abi:        artifact.abi,
    network:    "localhost",
    deployedAt: new Date().toISOString(),
    deployer:   deployer.address,
  };

  const configPath = path.join(__dirname, "..", "..", "pipeline", "contract_config.json");
  fs.writeFileSync(configPath, JSON.stringify(config, null, 2));
  console.log(`📄 Contract config written to: pipeline/contract_config.json`);
  console.log("\nYou can now start the Flask app: python app.py");
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
