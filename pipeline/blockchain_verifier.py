"""
blockchain_verifier.py
======================
Step 3 of the pipeline:
  a) Compute a deterministic SHA-256 hash of the discovered content metadata
  b) Store it on the local Hardhat EVM via ContentVerifier.storeRecord()
  c) Re-query the chain with ContentVerifier.verifyRecord() to prove the hash
     exists and is tamper-evident

Dependencies: web3 (pip install web3)
Pre-requisites (runtime):
  • Hardhat node running:  cd blockchain && npx hardhat node
  • Contract deployed:     cd blockchain && npm run deploy
  • pipeline/contract_config.json written by deploy.js
"""

import hashlib
import json
import logging
import os
import time

from web3 import Web3
from web3.exceptions import ContractLogicError

logger = logging.getLogger(__name__)

_CONFIG_PATH = os.path.join(os.path.dirname(__file__), "contract_config.json")


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _load_contract():
    """Connect to the local Hardhat node and return (web3, contract, account)."""
    rpc_url = os.environ.get("HARDHAT_RPC_URL", "http://127.0.0.1:8545")
    w3 = Web3(Web3.HTTPProvider(rpc_url))

    if not w3.is_connected():
        raise ConnectionError(
            f"Cannot connect to Hardhat node at {rpc_url}.\n"
            "Run:  cd blockchain && npx hardhat node"
        )

    if not os.path.exists(_CONFIG_PATH):
        raise FileNotFoundError(
            "pipeline/contract_config.json not found.\n"
            "Run:  cd blockchain && npm run deploy"
        )

    with open(_CONFIG_PATH) as fh:
        cfg = json.load(fh)

    contract = w3.eth.contract(
        address=w3.to_checksum_address(cfg["address"]),
        abi=cfg["abi"],
    )
    # Use the first pre-funded Hardhat account as the sender
    account = w3.eth.accounts[0]
    return w3, contract, account, cfg["address"]


def _content_hash(data: dict) -> str:
    """
    Deterministic SHA-256 of *data* (JSON with sorted keys).
    Returns a 64-char hex string suitable for bytes32 on-chain.
    """
    canonical = json.dumps(data, sort_keys=True, ensure_ascii=True)
    return hashlib.sha256(canonical.encode()).hexdigest()


def _hex_to_bytes32(hex_str: str) -> bytes:
    return bytes.fromhex(hex_str)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def store_on_chain(content_data: dict) -> dict:
    """
    Hash *content_data* and call ContentVerifier.storeRecord() on the local chain.

    Parameters
    ----------
    content_data : dict with at least 'url' and 'title' keys

    Returns
    -------
    dict with:
      success        (bool)
      content_hash   (str)   — 64-char hex SHA-256
      tx_hash        (str)   — Ethereum transaction hash
      block_number   (int)
      gas_used       (int)
      contract_addr  (str)
      error          (str)   — only on failure
    """
    try:
        w3, contract, account, contract_addr = _load_contract()
    except (ConnectionError, FileNotFoundError) as exc:
        return {"success": False, "error": str(exc)}

    c_hash = _content_hash(content_data)
    c_hash_bytes = _hex_to_bytes32(c_hash)

    url   = content_data.get("url", "")[:2048]   # guard against oversized strings
    title = content_data.get("title", "")[:512]

    logger.info(f"Storing content hash on chain: {c_hash[:16]}…")
    try:
        tx = contract.functions.storeRecord(
            c_hash_bytes, url, title
        ).transact({"from": account})

        receipt = w3.eth.wait_for_transaction_receipt(tx)
        logger.info(f"TX confirmed in block {receipt.blockNumber}")

        return {
            "success":       True,
            "content_hash":  c_hash,
            "tx_hash":       tx.hex(),
            "block_number":  receipt.blockNumber,
            "gas_used":      receipt.gasUsed,
            "contract_addr": contract_addr,
        }
    except ContractLogicError as exc:
        # Already stored (idempotent guard in contract)
        if "already exists" in str(exc):
            return {
                "success":      True,
                "content_hash": c_hash,
                "tx_hash":      "already-on-chain",
                "note":         "Record was previously stored on-chain.",
                "contract_addr": contract_addr,
            }
        return {"success": False, "error": str(exc)}
    except Exception as exc:
        logger.exception("Blockchain store error")
        return {"success": False, "error": str(exc)}


def verify_on_chain(content_hash: str) -> dict:
    """
    Call ContentVerifier.verifyRecord() to confirm the hash is on-chain.

    Parameters
    ----------
    content_hash : 64-char hex SHA-256 string (as returned by store_on_chain)

    Returns
    -------
    dict with:
      verified        (bool)
      url             (str)
      title           (str)
      timestamp       (int)   — Unix timestamp
      timestamp_human (str)   — human-readable UTC string
      error           (str)   — only on failure
    """
    try:
        w3, contract, _, _ = _load_contract()
    except (ConnectionError, FileNotFoundError) as exc:
        return {"verified": False, "error": str(exc)}

    try:
        exists, url, title, ts = contract.functions.verifyRecord(
            _hex_to_bytes32(content_hash)
        ).call()

        return {
            "verified":        exists,
            "url":             url,
            "title":           title,
            "timestamp":       ts,
            "timestamp_human": (
                time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime(ts)) if ts else None
            ),
        }
    except Exception as exc:
        logger.exception("Blockchain verify error")
        return {"verified": False, "error": str(exc)}
