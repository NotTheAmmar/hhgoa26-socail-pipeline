# Social Media Face OSINT Pipeline

This document explains the end-to-end architecture and data flow of the Face ID and Blockchain Evidence Verification pipeline. 

The primary goal of this system is to securely trace a given individual’s face to public social media posts across the web, verify the match cryptographically, and register the discovered evidence immutably on a blockchain (local EVM via Hardhat) to demonstrate tamper-evident OSINT verification.

---

## 1. Stage One: Face Detection & Encoding (`pipeline/face_detector.py`)

**Goal:** Accurately locate a human face in the uploaded image, crop it, and extract its unique biometric representation.

- **Detection:** We use `face_recognition` (powered by `dlib`'s HOG model) which is highly accurate for frontal faces. 
- **Cropping & Padding:** Once a face is detected, we expand the bounding box with a 30% padding. Cropping is essential because sending a full-body or noisy image to Google Lens confuses the search engine. By isolating the face, we force the reverse-image search to focus strictly on facial identity.
- **Biometric Encoding:** We generate a 128-dimensional embedding vector representing the facial features. This is serialized into JSON and passed down the pipeline so we can re-verify the person's identity in the search results later without needing the original image.

## 2. Stage Two: Web & Social Media Search (`pipeline/web_searcher.py`)

**Goal:** Find matching visual evidence of the person online, prioritizing social media, and mathematically verifying their identity.

- **Temporary Hosting:** Google Lens requires a public URL to perform a reverse image search. The cropped face is uploaded temporarily to `imgbb` using a free API.
- **Reverse Image Search (SerpAPI):** The public URL is passed to SerpAPI's Google Lens engine. This searches the web for matching or visually similar identities.
- **Identity Verification (Similarity Scoring):** For the top results returned by Lens, we download the thumbnail and run our facial recognition model against it. We calculate the Euclidean distance between the new face and the original 128-d encoding from Stage 1. This distance is converted into a **Face Similarity Percentage (0-100%)**.
- **Social Media Prioritization:** The results are strictly sorted to favor **Social Media posts first** (e.g., X, Instagram, LinkedIn, Reddit, Facebook). Within those categories, they are sorted by the highest Face Similarity score. If no social media posts are found, it falls back to general web results.

## 3. Stage Three: Cryptographic Hashing & Blockchain Verification (`pipeline/blockchain_verifier.py`)

**Goal:** Create a tamper-proof, immutable record of the highest-confidence OSINT finding.

- **Evidence Serialization:** The best match from Stage 2 (containing the URL, page title, social media source platform, face similarity score, and timestamp) is serialized into a normalized, deterministic JSON string.
- **SHA-256 Hashing:** We hash the JSON payload using `SHA-256` to create a 32-byte cryptographic digest (`bytes32`). Even changing a single character in the URL or title will completely change this hash (demonstrating tamper evidence).
- **Smart Contract (`ContentVerifier.sol`):** The hash is submitted via `web3.py` to our locally running Ethereum Virtual Machine (EVM) provided by Hardhat. 
- **Immutability:** The `storeRecord` function in the Solidity contract saves the hash and the exact `block.timestamp`. If anyone tries to store the exact same evidence hash again, the contract will revert.
- **Verification:** The pipeline immediately turns around and queries the blockchain using `verifyRecord(hash)` to prove that the evidence now exists on-chain and returns the block timestamp.

## 4. Stage Four: Orchestration & UI (`pipeline/orchestrator.py` & `app.py`)

**Goal:** Bring it all together into a clean, user-friendly interface.

- **Orchestrator:** The `run_pipeline()` function manages the state between the 3 stages, passing the cropped image from Stage 1 to Stage 2, and the best match from Stage 2 into Stage 3.
- **Flask App:** Provides a lightweight backend with a single `POST /run` endpoint to accept image uploads.
- **Frontend UI:** A dark-themed, single-page application (`templates/index.html`) using Vanilla JS. It displays the cropped face preview, visually ranks the match cards with similarity progress bars, and renders the Blockchain transaction details (Hash, Block Timestamp, and Verification Status).

## Limitations & Edge Cases

- **2D / Anime Characters:** The face detection model (`dlib` HOG/CNN via `face_recognition`) is biologically tuned to identify human facial structures (shadow gradients of noses, eye sockets, lip edges). It will intentionally fail to detect 2D illustrations or anime characters (like Tanjiro Kamado). This is working as intended, as the pipeline's goal is real-world Human OSINT, not artwork tracing.
- **Cross-Origin Images (CORS):** Some social media websites (like Instagram or LinkedIn) block hotlinking of their full-resolution images. In these cases, the UI gracefully falls back to displaying Google Lens' cached thumbnail.
