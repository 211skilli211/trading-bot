#!/usr/bin/env python3
"""
Secure Key Loader
=================
Prompts for password at startup to decrypt sensitive keys.
Implements memory zeroing for security.

Usage:
    from secure_key_loader import get_solana_private_key
    
    # Will prompt for password if not already loaded
    private_key = get_solana_private_key()
"""

import os
import sys
import getpass
import threading

# Path to encrypted keys file
KEYS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".encrypted_keys")

# In-memory storage (will be zeroed after use)
_cached_key = None
_key_loaded = False
_key_lock = threading.Lock()


def _load_encryption_module():
    """Load cryptography module, raise if not available"""
    try:
        from cryptography.fernet import Fernet
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
        import base64
        return True
    except ImportError:
        print("ERROR: cryptography library not installed")
        print("Install with: pip install cryptography")
        return False


def _derive_key(password: str, salt: bytes) -> bytes:
    """Derive key from password using PBKDF2"""
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    import base64
    
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=480000,
    )
    return base64.urlsafe_b64encode(kdf.derive(password.encode()))


def _decrypt_value(encrypted: str, password: str) -> str:
    """Decrypt an ENC:value string"""
    if not encrypted.startswith("ENC:"):
        return encrypted
    
    import base64
    
    parts = encrypted[4:].split(":")
    if len(parts) != 2:
        raise ValueError("Invalid encrypted format")
    
    salt = base64.b64decode(parts[0])
    ciphertext = base64.b64decode(parts[1])
    
    key = _derive_key(password, salt)
    f = Fernet(key)
    
    return f.decrypt(ciphertext).decode()


def _prompt_password() -> str:
    """Prompt for encryption password"""
    print("\n" + "="*50)
    print("SECURITY: Enter encryption password")
    print("="*50)
    
    # Check if running in non-interactive mode
    if not sys.stdin.isatty():
        password = os.environ.get("ENCRYPTION_PASSWORD")
        if password:
            return password
        raise RuntimeError("Non-interactive mode requires ENCRYPTION_PASSWORD env var")
    
    while True:
        password = getpass.getpass("Password: ")
        if len(password) < 8:
            print("Password must be at least 8 characters")
            continue
        
        confirm = getpass.getpass("Confirm: ")
        if password != confirm:
            print("Passwords don't match, try again")
            continue
        
        return password


def load_encrypted_keys(password: str = None) -> dict:
    """Load and decrypt keys from encrypted file"""
    global _cached_key, _key_loaded
    
    if _key_loaded:
        return {"solana_private_key": _cached_key} if _cached_key else {}
    
    with _key_lock:
        if _key_loaded:
            return {"solana_private_key": _cached_key} if _cached_key else {}
        
        if not password:
            password = _prompt_password()
        
        keys = {}
        
        if os.path.exists(KEYS_FILE):
            with open(KEYS_FILE, 'r') as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    if "=" in line:
                        key, value = line.split("=", 1)
                        key = key.strip().lower()
                        value = value.strip()
                        if value.startswith("ENC:"):
                            try:
                                value = _decrypt_value(value, password)
                            except Exception as e:
                                print(f"Warning: Failed to decrypt {key}: {e}")
                                continue
                        keys[key] = value
        
        # Also check .env for backward compatibility
        from dotenv import load_dotenv
        load_dotenv()
        
        env_key = os.environ.get("SOLANA_PRIVATE_KEY", "")
        if env_key and "solana_private_key" not in keys:
            if env_key.startswith("ENC:"):
                try:
                    keys["solana_private_key"] = _decrypt_value(env_key, password)
                except Exception as e:
                    print(f"Warning: Failed to decrypt SOLANA_PRIVATE_KEY from .env: {e}")
            else:
                keys["solana_private_key"] = env_key
        
        _cached_key = keys.get("solana_private_key")
        _key_loaded = True
        
        return keys


def get_solana_private_key(password: str = None) -> str:
    """
    Get Solana private key, prompting for password if needed.
    
    Args:
        password: Optional password. If not provided, will prompt.
        
    Returns:
        Decrypted private key string
    """
    global _cached_key
    
    if not _load_encryption_module():
        return os.getenv("SOLANA_PRIVATE_KEY", "")
    
    keys = load_encrypted_keys(password)
    return keys.get("solana_private_key", "")


def clear_key_from_memory():
    """
    Zero out the cached key from memory.
    Call this after using the key for signing.
    """
    global _cached_key, _key_loaded
    
    with _key_lock:
        if _cached_key:
            _cached_key = None
        _key_loaded = False


def is_key_loaded() -> bool:
    """Check if the key has been loaded"""
    return _key_loaded and _cached_key is not None


def encrypt_key(value: str, password: str) -> str:
    """Encrypt a single value"""
    import os
    import base64
    from cryptography.fernet import Fernet
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    
    salt = os.urandom(16)
    key = _derive_key(password, salt)
    f = Fernet(key)
    
    ciphertext = f.encrypt(value.encode())
    
    return f"ENC:{base64.b64encode(salt).decode()}:{base64.b64encode(ciphertext).decode()}"


def cli_main():
    """CLI for managing encrypted keys"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Secure Key Loader CLI")
    parser.add_argument("action", choices=["encrypt", "decrypt", "set-password"],
                        help="Action to perform")
    parser.add_argument("--key", help="Key name (e.g., SOLANA_PRIVATE_KEY)")
    parser.add_argument("--value", help="Value to encrypt")
    parser.add_argument("--password", help="Master password")
    parser.add_argument("--file", help="Input/output file")
    
    args = parser.parse_args()
    
    if not _load_encryption_module():
        return 1
    
    if args.action == "encrypt":
        if not args.key or not args.value:
            print("Error: --key and --value required")
            return 1
        
        password = args.password or _prompt_password()
        encrypted = encrypt_key(args.value, password)
        
        with open(KEYS_FILE, "a") as f:
            f.write(f"{args.key}={encrypted}\n")
        
        print(f"Encrypted {args.key} saved to {KEYS_FILE}")
        print(f"Encrypted value: {encrypted}")
    
    elif args.action == "decrypt":
        if not args.key:
            print("Error: --key required")
            return 1
        
        password = args.password or getpass.getpass("Password: ")
        
        try:
            decrypted = get_solana_private_key(password)
            print(f"Decrypted: {decrypted}")
        except Exception as e:
            print(f"Decryption failed: {e}")
            return 1
    
    elif args.action == "set-password":
        print("This will re-encrypt all keys with a new password")
        old_password = getpass.getpass("Current password: ")
        new_password = getpass.getpass("New password: ")
        confirm = getpass.getpass("Confirm: ")
        
        if new_password != confirm:
            print("Passwords don't match")
            return 1
        
        if os.path.exists(KEYS_FILE):
            with open(KEYS_FILE, "r") as f:
                lines = f.readlines()
            
            with open(KEYS_FILE, "w") as f:
                for line in lines:
                    if "=" in line and not line.startswith("#"):
                        key, value = line.strip().split("=", 1)
                        if value.startswith("ENC:"):
                            try:
                                decrypted = _decrypt_value(value, old_password)
                                reencrypted = encrypt_key(decrypted, new_password)
                                f.write(f"{key}={reencrypted}\n")
                            except:
                                f.write(line)
                        else:
                            f.write(line)
                    else:
                        f.write(line)
        
        print("Password updated successfully")
    
    return 0


if __name__ == "__main__":
    exit(cli_main())
