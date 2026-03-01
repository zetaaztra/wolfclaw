import os
import base64
import json
from pathlib import Path
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.backends import default_backend

VAULT_DIR = Path("data/vault")
VAULT_DIR.mkdir(parents=True, exist_ok=True)
KEY_FILE = VAULT_DIR / ".master.key"
VAULT_FILE = VAULT_DIR / "secrets.enc"

def _generate_master_key():
    """Generates a master key derived from machine-specific identifiers (simulated as simple for now)."""
    # In a production-grade 'Sovereign OS', we would use TPM or OS Keyring
    # For now, we generate a random key once if not present.
    if not KEY_FILE.exists():
        key = AESGCM.generate_key(bit_length=256)
        with open(KEY_FILE, "wb") as f:
            f.write(base64.b64encode(key))
    
    with open(KEY_FILE, "rb") as f:
        return base64.b64decode(f.read())

def encrypt_key(provider: str, key_value: str):
    """Encrypts and stores an API key in the vault."""
    master_key = _generate_master_key()
    aesgcm = AESGCM(master_key)
    nonce = os.urandom(12)
    
    encrypted = aesgcm.encrypt(nonce, key_value.encode(), provider.encode())
    
    # Load existing secrets
    secrets = {}
    if VAULT_FILE.exists():
        try:
            with open(VAULT_FILE, "r") as f:
                secrets = json.load(f)
        except:
            secrets = {}
            
    secrets[provider] = {
        "nonce": base64.b64encode(nonce).decode('utf-8'),
        "data": base64.b64encode(encrypted).decode('utf-8')
    }
    
    with open(VAULT_FILE, "w") as f:
        json.dump(secrets, f)

def decrypt_key(provider: str) -> str:
    """Decrypts and returns an API key from the vault."""
    if not VAULT_FILE.exists():
        return ""
        
    try:
        master_key = _get_master_key_cached()
        with open(VAULT_FILE, "r") as f:
            secrets = json.load(f)
            
        if provider not in secrets:
            return ""
            
        secret = secrets[provider]
        nonce = base64.b64decode(secret["nonce"])
        encrypted_data = base64.b64decode(secret["data"])
        
        aesgcm = AESGCM(master_key)
        decrypted = aesgcm.decrypt(nonce, encrypted_data, provider.encode())
        return decrypted.decode('utf-8')
    except Exception as e:
        print(f"VAULT ERROR: Failed to decrypt {provider}: {e}")
        return ""

_master_key_cache = None
def _get_master_key_cached():
    global _master_key_cache
    if _master_key_cache is None:
        _master_key_cache = _generate_master_key()
    return _master_key_cache

def list_vaulted_providers():
    """Returns a list of providers that have keys in the vault."""
    if not VAULT_FILE.exists():
        return []
    try:
        with open(VAULT_FILE, "r") as f:
            secrets = json.load(f)
            return list(secrets.keys())
    except:
        return []
