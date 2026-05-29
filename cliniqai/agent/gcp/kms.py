import os
import base64
import json
from google.cloud import kms
from google.api_core.exceptions import GoogleAPIError

from agent.gcp.logger import get_logger

logger = get_logger(__name__)

def _get_key_name():
    project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
    location = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")
    key_ring = os.getenv("KMS_KEY_RING", "cliniqai-keyring")
    key_name = os.getenv("KMS_KEY_NAME", "patient-data-key")
    
    if not project_id or project_id == "your_project_id_here":
        return None
    
    return f"projects/{project_id}/locations/{location}/keyRings/{key_ring}/cryptoKeys/{key_name}"

def encrypt_data(data: dict) -> dict:
    """
    Encrypts a dictionary of patient data using Google Cloud KMS.
    If KMS is not available, falls back to base64 encoding (for demo/local testing).
    """
    key_name = _get_key_name()
    plaintext_bytes = json.dumps(data).encode('utf-8')
    
    if key_name:
        try:
            client = kms.KeyManagementServiceClient()
            response = client.encrypt(
                request={'name': key_name, 'plaintext': plaintext_bytes}
            )
            # Prefix with 'gcp-kms:' so we know how to decrypt it
            encrypted_b64 = base64.b64encode(response.ciphertext).decode('utf-8')
            logger.info(f"🔒 Data encrypted successfully using KMS.")
            return {"_encrypted_payload": f"gcp-kms:{encrypted_b64}"}
        except GoogleAPIError as e:
            logger.error(f"KMS Encryption failed: {e}. Falling back to base64 mock encryption.")
        except Exception as e:
            logger.error(f"Unexpected error in KMS Encryption: {e}. Falling back to base64.")
            
    # Mock encryption for local testing/demo if GCP fails
    logger.info("ℹ️ Using mock base64 encryption (KMS unavailable).")
    mock_encrypted = base64.b64encode(plaintext_bytes).decode('utf-8')
    return {"_encrypted_payload": f"mock-b64:{mock_encrypted}"}

def decrypt_data(encrypted_data: dict) -> dict:
    """
    Decrypts patient data using Google Cloud KMS.
    """
    if "_encrypted_payload" not in encrypted_data:
        return encrypted_data # Already plaintext or unstructured
        
    payload = encrypted_data["_encrypted_payload"]
    
    if payload.startswith("gcp-kms:"):
        key_name = _get_key_name()
        if not key_name:
            logger.error("KMS key configured needed but GCP project missing.")
            return {"error": "Decryption failed - missing GCP Config"}
            
        try:
            ciphertext = base64.b64decode(payload.split(":", 1)[1])
            client = kms.KeyManagementServiceClient()
            response = client.decrypt(
                request={'name': key_name, 'ciphertext': ciphertext}
            )
            logger.info("🔓 Data decrypted successfully using KMS.")
            return json.loads(response.plaintext.decode('utf-8'))
        except Exception as e:
            logger.error(f"KMS Decryption failed: {e}")
            return {"error": f"Decryption failed: {str(e)}"}
            
    elif payload.startswith("mock-b64:"):
        logger.info("🔓 Data decrypted successfully using mock base64.")
        plaintext_bytes = base64.b64decode(payload.split(":", 1)[1])
        return json.loads(plaintext_bytes.decode('utf-8'))
        
    return encrypted_data
