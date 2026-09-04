import hashlib
import json

def generate_evidence_hash(payload):
    """
    Constructs a normalized JSON payload and computes its deterministic SHA-256 hash.
    """
    # Normalize by sorting keys and removing extraneous whitespace
    canonical_json = json.dumps(payload, sort_keys=True, separators=(',', ':'))
    
    # Compute SHA-256 digest
    digest = hashlib.sha256(canonical_json.encode('utf-8')).hexdigest()
    return f"0x{digest}", canonical_json
