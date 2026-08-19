import logging
from cryptography.fernet import Fernet
from backend.config import settings

logger = logging.getLogger("security")

# Initialize Fernet cipher if a key is configured
_cipher = None
if settings.TOKEN_ENCRYPTION_KEY:
    try:
        _cipher = Fernet(settings.TOKEN_ENCRYPTION_KEY.encode())
    except Exception as e:
        logger.error(f"Failed to initialize Fernet cipher: {e}")

def encrypt_secret(plaintext: str) -> str:
    """
    Encrypts the plaintext value using Fernet.
    """
    if not plaintext:
        return plaintext

    if not _cipher:
        # Fail safe
        raise ValueError("Encryption cipher is not initialized. TOKEN_ENCRYPTION_KEY may be missing or invalid.")

    try:
        encrypted_bytes = _cipher.encrypt(plaintext.encode('utf-8'))
        return encrypted_bytes.decode('utf-8')
    except Exception as e:
        logger.error(f"Failed to encrypt secret: {e}")
        raise ValueError(f"Encryption failed: {e}")

def decrypt_secret(ciphertext: str) -> str:
    """
    Decrypts the value using Fernet. 
    If the value is not encrypted or decryption fails, returns the value as-is for legacy fallback.
    """
    if not ciphertext:
        return ciphertext

    # Fernet tokens always start with gAAAAA
    if not ciphertext.startswith("gAAAAA"):
        return ciphertext

    if not _cipher:
        logger.warning("Decryption cipher not initialized, returning raw ciphertext as legacy fallback.")
        return ciphertext

    try:
        decrypted_bytes = _cipher.decrypt(ciphertext.encode('utf-8'))
        return decrypted_bytes.decode('utf-8')
    except Exception as e:
        # Decryption failed (could be legacy value that coincidentally starts with gAAAAA, or key mismatch)
        logger.warning(f"Decryption failed, returning value as-is: {e}")
        return ciphertext
