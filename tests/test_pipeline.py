import pytest
import os
import cv2
import numpy as np
from src.detector import detect_and_crop_face
from src.hasher import generate_evidence_hash
from src.blockchain import BlockchainClient

def test_hash_generation():
    payload = {
        "source_platform": "Twitter",
        "post_url": "https://x.com/mockuser/status/123456789",
        "title": "Mock User post about the event",
        "thumbnail_url": "https://example.com/mock_thumb.jpg",
        "timestamp": "2023-10-01"
    }
    digest1, json1 = generate_evidence_hash(payload)
    digest2, json2 = generate_evidence_hash(payload)
    
    assert digest1 == digest2
    assert type(digest1) == str
    assert digest1.startswith("0x")

def test_blockchain_mock_verification():
    client = BlockchainClient(use_mock=True)
    client.deploy_contract()
    
    test_digest = "0x" + "a" * 64
    client.record_evidence(test_digest)
    
    exists, timestamp = client.verify_evidence(test_digest)
    assert exists == True
    assert timestamp > 0
    
    # Check invalid digest
    bad_digest = "0x" + "b" * 64
    exists, _ = client.verify_evidence(bad_digest)
    assert exists == False

def test_face_detection_no_face():
    # Create a dummy image without a face
    dummy_image = np.zeros((100, 100, 3), dtype=np.uint8)
    temp_path = "temp_dummy.jpg"
    cv2.imwrite(temp_path, dummy_image)
    
    try:
        cropped, found = detect_and_crop_face(temp_path)
        assert found == False
        assert cropped.shape == (100, 100, 3)
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)
