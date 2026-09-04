import argparse
import os
import copy
from src.detector import detect_and_crop_face
from src.searcher import reverse_image_search
from src.hasher import generate_evidence_hash
from src.blockchain import BlockchainClient

def main():
    parser = argparse.ArgumentParser(description="Visual OSINT & Blockchain Evidence Verification CLI")
    parser.add_argument("--image", required=True, help="Path to the input image")
    parser.add_argument("--mock", action="store_true", help="Use mock data to avoid API credits/live network")
    parser.add_argument("--tamper-test", action="store_true", help="Demonstrate tamper detection by altering the payload before verification")
    
    args = parser.parse_args()

    # Step 1: Detect Face
    print("\n[1/4] Detecting Face...")
    try:
        cropped_img, found = detect_and_crop_face(args.image)
        if found:
            print("      -> Face detected successfully. Proceeding with cropped image.")
            import cv2
            temp_image = "temp_cropped_face.jpg"
            cv2.imwrite(temp_image, cropped_img)
            search_image_path = temp_image
        else:
            print("      -> No face detected. Proceeding with original image.")
            search_image_path = args.image
    except Exception as e:
        print(f"      -> Error in face detection: {e}")
        return

    # Step 2: OSINT Search
    print("\n[2/4] OSINT Search (Google Lens via SerpApi)...")
    try:
        payload = reverse_image_search(search_image_path, mock=args.mock)
        if not payload:
            print("      -> No matching visual evidence found.")
            return
        print(f"      -> Found Matching Evidence:")
        print(f"         Platform: {payload['source_platform']}")
        print(f"         Post URL: {payload['post_url']}")
        print(f"         Title: {payload['title']}")
    except Exception as e:
        print(f"      -> Error during OSINT search: {e}")
        return

    # Step 3: Cryptographic Hashing
    print("\n[3/4] Cryptographic Hashing...")
    try:
        original_digest, canonical_json = generate_evidence_hash(payload)
        print(f"      -> Normalized Payload:")
        print(f"         {canonical_json}")
        print(f"      -> SHA-256 Digest: {original_digest}")
    except Exception as e:
        print(f"      -> Error during hashing: {e}")
        return

    # Step 4: Blockchain Verification
    print("\n[4/4] Blockchain Verification...")
    try:
        client = BlockchainClient(use_mock=args.mock)
        client.deploy_contract()
        
        # Record the canonical original hash
        client.record_evidence(original_digest)
        
        # Verify the original payload
        print("\n--- Verification: Original Payload ---")
        client.verify_evidence(original_digest)
        
        if args.tamper_test:
            print("\n--- Verification: Tampered Payload ---")
            tampered_payload = copy.deepcopy(payload)
            # Mutate one character in the discovered post URL
            tampered_payload['post_url'] = tampered_payload['post_url'] + "X"
            
            tampered_digest, tampered_json = generate_evidence_hash(tampered_payload)
            print(f"      -> Tampered Payload:")
            print(f"         {tampered_json}")
            print(f"      -> Tampered SHA-256 Digest: {tampered_digest}")
            
            client.verify_evidence(tampered_digest)

    except Exception as e:
        print(f"      -> Error during blockchain operations: {e}")
        return
        
    finally:
        # Cleanup temp cropped image if it exists
        if 'search_image_path' in locals() and search_image_path == "temp_cropped_face.jpg" and os.path.exists("temp_cropped_face.jpg"):
            os.remove("temp_cropped_face.jpg")

if __name__ == "__main__":
    main()
