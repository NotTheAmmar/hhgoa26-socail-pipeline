# Visual OSINT & Blockchain Evidence Verification

A production-grade CLI pipeline designed for a hackathon that performs automated open-source intelligence (OSINT) on visual data, cryptographically fingerprints the findings, and securely logs the evidence onto an EVM-compatible blockchain.

## What the Project Does
The pipeline accepts an arbitrary input image (containing a human face). It follows a 4-step workflow:
1. **Face Isolation**: Uses local Computer Vision (OpenCV Haar Cascades) to detect a face, calculate a bounding box, pad the image, and isolate the face.
2. **Reverse Image Search**: Uses Google Lens (via SerpApi) to perform a reverse image search on the isolated face. It filters the results to prioritize OSINT data from major social media domains (X, Instagram, LinkedIn, Reddit, Facebook).
3. **Cryptographic Fingerprinting**: Extracts a canonical JSON payload of the matched evidence (platform, URL, title, timestamp) and generates a deterministic SHA-256 hash.
4. **Blockchain Verification**: Connects to an EVM-compatible blockchain to record the evidence hash in a Solidity smart contract, permanently verifying its timestamp and integrity. 

## How to Run It

### 1. Install Dependencies
Ensure you have Python installed, then run:
```bash
pip install -r requirements.txt
```

### 2. Configure Environment
Copy the example environment variables file and fill in your keys:
```bash
cp .env.example .env
```
- `SERPAPI_KEY`: Your SerpApi key (required for live reverse image searches).
- `RPC_URL`: Your EVM JSON-RPC URL (defaults to localhost:8545).
- `PRIVATE_KEY`: The wallet private key used for deploying and writing to the contract.

### 3. Usage Commands
**Run with Local Mock Data (No API keys needed):**
Use the `--mock` flag to run a fully simulated pipeline locally. It will use a mock SerpApi response and a local in-memory Ethereum tester node.
```bash
python main.py --image sample_images/test.jpg --mock
```

**Run with Live API & RPC:**
```bash
python main.py --image sample_images/test.jpg
```

**Tamper Test Verification:**
Pass `--tamper-test` to see the pipeline detect modified evidence on-chain. This will hash the original, record it, then artificially mutate the payload and prove that the tampered version is rejected by the blockchain.
```bash
python main.py --image sample_images/test.jpg --mock --tamper-test
```

### 4. Running Tests
Run the unit test suite using `pytest`:
```bash
pytest tests/
```

## Which Blockchain We Used
The architecture is inherently **blockchain-agnostic** across all EVM-compatible networks. 
- **Local/Mock Environment**: By default, when testing locally (or using the `--mock` flag), the pipeline uses `eth-tester` with a `py-evm` backend. This creates an ephemeral, in-memory local blockchain that executes the smart contract without needing external infrastructure.
- **Production Environment**: You can seamlessly deploy this to **Ethereum, Polygon, Arbitrum, Optimism, Base**, or any other EVM chain by simply updating the `RPC_URL` and `PRIVATE_KEY` in the `.env` file. The provided `BlockchainClient` uses standard `web3.py` libraries to interact with any standard Ethereum RPC.

## Known Limitations
1. **Face Detection Efficacy**: The Haar Cascades model is lightweight and completely free, making it great for a hackathon. However, it can struggle with heavy occlusions, profile angles, or poor lighting. A more advanced model like RetinaFace or MTCNN would be required for a production-grade facial recognition system.
2. **SerpApi Upload Limitations**: SerpApi's Google Lens endpoint does not natively allow raw image blob uploads; it expects public image URLs. To bypass this, we utilize a workaround to get an `image_id`. This workflow could be brittle if SerpApi changes their undocumented upload endpoints.
3. **Data Mutability Before Hashing**: The hash is only as trustworthy as the data payload constructed by the OSINT search. If the Google Lens metadata is manipulated prior to the SHA-256 generation, the blockchain will verify a false truth. 
4. **Gas Costs for Heavy Usage**: While writing a 32-byte hash is extremely cheap on Layer-2s, a large-scale system processing thousands of images a minute would need batching (e.g., Merkle Trees) rather than recording each individual hash in a separate transaction.
