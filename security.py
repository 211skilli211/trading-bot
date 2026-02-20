#!/usr/bin/env python3
"""
API Key Encryption Module
=========================
Provides encryption/decryption for API keys using Fernet symmetric encryption.

Usage:
    from security import encrypt_api_key, decrypt_api_key, load_encrypted_env
    
    # Encrypt an API key
    encrypted = encrypt_api_key("my-api-key", password="master-password")
    
    # Decrypt an API key
    decrypted = decrypt_api_key(encrypted, password="master-password")
    
    # Load .env file with encrypted values
    load_encrypted_env(password="master-password")
"""

import os
import base64
import hashlib
from pathlib import Path
from typing import Optional

try:
    from cryptography.fernet import Fernet
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    CRYPTO_AVAILABLE = True
except ImportError:
    CRYPTO_AVAILABLE = False
    print("Warning: cryptography library not installed. Encryption features disabled.")
    print("Install with: pip install cryptography")

try:
    from dotenv import load_dotenv
    DOTENV_AVAILABLE = True
except ImportError:
    DOTENV_AVAILABLE = False


# Constants
ENCRYPTED_PREFIX = "ENC:"
SALT_LENGTH = 16
ITERATIONS = 480000  # PBKDF2 iterations (high for security)


def _derive_key(password: str, salt: bytes) -> bytes:
    """
    Derive a Fernet key from a password and salt using PBKDF2.
    
    Args:
        password: The master password
        salt: Random salt bytes
        
    Returns:
        URL-safe base64-encoded key for Fernet
    """
    if not CRYPTO_AVAILABLE:
        raise RuntimeError("cryptography library not available")
    
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=ITERATIONS,
    )
    key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
    return key


def encrypt_api_key(plaintext: str, password: str) -> str:
    """
    Encrypt an API key using Fernet encryption.
    
    Args:
        plaintext: The API key or secret to encrypt
        password: Master password for encryption
        
    Returns:
        Encrypted string with format: ENC:<salt>:<ciphertext>
        
    Example:
        >>> encrypted = encrypt_api_key("my-secret-key", "my-master-password")
        >>> print(encrypted)
        'ENC:aGVsbG8...:gAAAAABk...'
    """
    if not CRYPTO_AVAILABLE:
        raise RuntimeError("cryptography library not installed")
    
    if not plaintext:
        return plaintext
    
    # Generate random salt
    salt = os.urandom(SALT_LENGTH)
    
    # Derive key from password
    key = _derive_key(password, salt)
    
    # Encrypt the plaintext
    fernet = Fernet(key)
    ciphertext = fernet.encrypt(plaintext.encode())
    
    # Format: ENC:<base64-salt>:<base64-ciphertext>
    encrypted_value = f"{ENCRYPTED_PREFIX}{base64.urlsafe_b64encode(salt).decode()}:{ciphertext.decode()}"
    
    return encrypted_value


def decrypt_api_key(encrypted: str, password: str) -> str:
    """
    Decrypt an encrypted API key.
    
    Args:
        encrypted: Encrypted string (format: ENC:<salt>:<ciphertext>)
        password: Master password for decryption
        
    Returns:
        Decrypted plaintext string
        
    Raises:
        ValueError: If the encrypted format is invalid
        RuntimeError: If decryption fails (wrong password or corrupted data)
        
    Example:
        >>> decrypted = decrypt_api_key("ENC:aGVsbG8...:gAAAAABk...", "my-master-password")
        >>> print(decrypted)
        'my-secret-key'
    """
    if not CRYPTO_AVAILABLE:
        raise RuntimeError("cryptography library not installed")
    
    if not encrypted or not encrypted.startswith(ENCRYPTED_PREFIX):
        # Return as-is if not encrypted
        return encrypted
    
    try:
        # Remove prefix and split
        parts = encrypted[len(ENCRYPTED_PREFIX):].split(":", 1)
        if len(parts) != 2:
            raise ValueError("Invalid encrypted format")
        
        salt_b64, ciphertext = parts
        salt = base64.urlsafe_b64decode(salt_b64)
        
        # Derive key
        key = _derive_key(password, salt)
        
        # Decrypt
        fernet = Fernet(key)
        plaintext = fernet.decrypt(ciphertext.encode()).decode()
        
        return plaintext
        
    except Exception as e:
        raise RuntimeError(f"Decryption failed: {e}")


def is_encrypted(value: str) -> bool:
    """
    Check if a value is encrypted.
    
    Args:
        value: The value to check
        
    Returns:
        True if encrypted, False otherwise
    """
    return isinstance(value, str) and value.startswith(ENCRYPTED_PREFIX)


def load_encrypted_env(
    dotenv_path: Optional[str] = None,
    password: Optional[str] = None,
    password_env_var: str = "ENCRYPTION_PASSWORD"
) -> dict:
    """
    Load environment variables from .env file with automatic decryption.
    
    This function loads the .env file and automatically decrypts any
    encrypted values (those starting with 'ENC:').
    
    Args:
        dotenv_path: Path to .env file (default: .env in current directory)
        password: Master password for decryption (if None, reads from password_env_var)
        password_env_var: Environment variable name containing the password
        
    Returns:
        Dictionary of decrypted environment variables
        
    Example:
        >>> # With ENCRYPTION_PASSWORD environment variable set
        >>> env = load_encrypted_env()
        >>> print(env['BINANCE_API_KEY'])
        'decrypted-api-key'
    """
    if not DOTENV_AVAILABLE:
        raise RuntimeError("python-dotenv library not installed")
    
    # Load .env file
    if dotenv_path is None:
        dotenv_path = ".env"
    
    dotenv_path = Path(dotenv_path)
    if dotenv_path.exists():
        load_dotenv(dotenv_path, override=True)
    
    # Get password
    if password is None:
        password = os.getenv(password_env_var)
    
    # Get all environment variables
    env_vars = dict(os.environ)
    
    # Decrypt encrypted values
    if password and CRYPTO_AVAILABLE:
        for key, value in env_vars.items():
            if isinstance(value, str) and is_encrypted(value):
                try:
                    decrypted = decrypt_api_key(value, password)
                    os.environ[key] = decrypted
                    env_vars[key] = decrypted
                except Exception as e:
                    print(f"Warning: Failed to decrypt {key}: {e}")
    
    return env_vars


def encrypt_env_file(
    keys_to_encrypt: list,
    password: str,
    input_path: str = ".env",
    output_path: Optional[str] = None
) -> int:
    """
    Encrypt specific keys in a .env file.
    
    Args:
        keys_to_encrypt: List of environment variable names to encrypt
        password: Master password for encryption
        input_path: Path to input .env file
        output_path: Path to output .env file (default: overwrite input)
        
    Returns:
        Number of values encrypted
        
    Example:
        >>> encrypt_env_file(
        ...     keys_to_encrypt=['BINANCE_API_KEY', 'BINANCE_SECRET'],
        ...     password='my-master-password',
        ...     input_path='.env',
        ...     output_path='.env.encrypted'
        ... )
    """
    if not CRYPTO_AVAILABLE:
        raise RuntimeError("cryptography library not installed")
    
    input_path = Path(input_path)
    if not input_path.exists():
        raise FileNotFoundError(f".env file not found: {input_path}")
    
    if output_path is None:
        output_path = input_path
    
    encrypted_count = 0
    lines = []
    
    with open(input_path, 'r') as f:
        for line in f:
            line = line.rstrip('\n')
            
            # Skip comments and empty lines
            if not line.strip() or line.strip().startswith('#'):
                lines.append(line)
                continue
            
            # Parse key=value
            if '=' in line:
                key, value = line.split('=', 1)
                key = key.strip()
                
                if key in keys_to_encrypt and value and not is_encrypted(value):
                    # Encrypt this value
                    encrypted = encrypt_api_key(value, password)
                    lines.append(f"{key}={encrypted}")
                    encrypted_count += 1
                else:
                    lines.append(line)
            else:
                lines.append(line)
    
    # Write output
    with open(output_path, 'w') as f:
        f.write('\n'.join(lines) + '\n')
    
    return encrypted_count


def decrypt_env_file(
    password: str,
    input_path: str = ".env",
    output_path: Optional[str] = None
) -> int:
    """
    Decrypt all encrypted values in a .env file.
    
    Args:
        password: Master password for decryption
        input_path: Path to input .env file
        output_path: Path to output .env file (default: overwrite input)
        
    Returns:
        Number of values decrypted
    """
    if not CRYPTO_AVAILABLE:
        raise RuntimeError("cryptography library not installed")
    
    input_path = Path(input_path)
    if not input_path.exists():
        raise FileNotFoundError(f".env file not found: {input_path}")
    
    if output_path is None:
        output_path = input_path
    
    decrypted_count = 0
    lines = []
    
    with open(input_path, 'r') as f:
        for line in f:
            line = line.rstrip('\n')
            
            # Skip comments and empty lines
            if not line.strip() or line.strip().startswith('#'):
                lines.append(line)
                continue
            
            # Parse key=value
            if '=' in line:
                key, value = line.split('=', 1)
                
                if is_encrypted(value):
                    # Decrypt this value
                    try:
                        decrypted = decrypt_api_key(value, password)
                        lines.append(f"{key}={decrypted}")
                        decrypted_count += 1
                    except Exception as e:
                        print(f"Warning: Failed to decrypt {key.strip()}: {e}")
                        lines.append(line)
                else:
                    lines.append(line)
            else:
                lines.append(line)
    
    # Write output
    with open(output_path, 'w') as f:
        f.write('\n'.join(lines) + '\n')
    
    return decrypted_count


def generate_key() -> str:
    """
    Generate a new random Fernet key.
    
    Returns:
        URL-safe base64-encoded key
        
    Note:
        This is useful for generating a master encryption key that can be
        stored securely (e.g., in a password manager or HSM).
    """
    if not CRYPTO_AVAILABLE:
        raise RuntimeError("cryptography library not installed")
    
    return Fernet.generate_key().decode()


# ============================================================================
# CLI INTERFACE
# ============================================================================

def main():
    """CLI entry point for encryption operations."""
    import argparse
    import getpass
    
    parser = argparse.ArgumentParser(
        description="API Key Encryption Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Encrypt values in .env file
  python security.py encrypt --keys BINANCE_API_KEY BINANCE_SECRET SOLANA_PRIVATE_KEY
  
  # Decrypt values in .env file
  python security.py decrypt
  
  # Encrypt a single value
  python security.py encrypt-value "my-secret-key"
  
  # Decrypt a single value
  python security.py decrypt-value "ENC:abc123:..."
  
  # Generate a random encryption key
  python security.py generate-key
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Command to run')
    
    # Encrypt command
    encrypt_parser = subparsers.add_parser('encrypt', help='Encrypt values in .env file')
    encrypt_parser.add_argument('--keys', '-k', nargs='+', required=True,
                               help='Keys to encrypt (e.g., BINANCE_API_KEY)')
    encrypt_parser.add_argument('--input', '-i', default='.env',
                               help='Input .env file (default: .env)')
    encrypt_parser.add_argument('--output', '-o',
                               help='Output .env file (default: overwrite input)')
    encrypt_parser.add_argument('--password', '-p',
                               help='Encryption password (will prompt if not provided)')
    
    # Decrypt command
    decrypt_parser = subparsers.add_parser('decrypt', help='Decrypt values in .env file')
    decrypt_parser.add_argument('--input', '-i', default='.env',
                               help='Input .env file (default: .env)')
    decrypt_parser.add_argument('--output', '-o',
                               help='Output .env file (default: overwrite input)')
    decrypt_parser.add_argument('--password', '-p',
                               help='Decryption password (will prompt if not provided)')
    
    # Encrypt single value
    encrypt_val_parser = subparsers.add_parser('encrypt-value', help='Encrypt a single value')
    encrypt_val_parser.add_argument('value', help='Value to encrypt')
    encrypt_val_parser.add_argument('--password', '-p',
                                   help='Encryption password (will prompt if not provided)')
    
    # Decrypt single value
    decrypt_val_parser = subparsers.add_parser('decrypt-value', help='Decrypt a single value')
    decrypt_val_parser.add_argument('value', help='Value to decrypt')
    decrypt_val_parser.add_argument('--password', '-p',
                                   help='Decryption password (will prompt if not provided)')
    
    # Generate key
    subparsers.add_parser('generate-key', help='Generate a random encryption key')
    
    # Check command
    check_parser = subparsers.add_parser('check', help='Check which values are encrypted')
    check_parser.add_argument('--input', '-i', default='.env',
                             help='Input .env file (default: .env)')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    if not CRYPTO_AVAILABLE:
        print("❌ Error: cryptography library not installed")
        print("Install with: pip install cryptography")
        return 1
    
    # Execute command
    if args.command == 'encrypt':
        password = args.password or getpass.getpass("Enter encryption password: ")
        if not password:
            print("❌ Password required")
            return 1
        
        try:
            count = encrypt_env_file(args.keys, password, args.input, args.output)
            print(f"✅ Encrypted {count} value(s) in {args.output or args.input}")
        except Exception as e:
            print(f"❌ Error: {e}")
            return 1
    
    elif args.command == 'decrypt':
        password = args.password or getpass.getpass("Enter decryption password: ")
        if not password:
            print("❌ Password required")
            return 1
        
        try:
            count = decrypt_env_file(password, args.input, args.output)
            print(f"✅ Decrypted {count} value(s) in {args.output or args.input}")
        except Exception as e:
            print(f"❌ Error: {e}")
            return 1
    
    elif args.command == 'encrypt-value':
        password = args.password or getpass.getpass("Enter encryption password: ")
        if not password:
            print("❌ Password required")
            return 1
        
        try:
            encrypted = encrypt_api_key(args.value, password)
            print(f"Encrypted value:\n{encrypted}")
        except Exception as e:
            print(f"❌ Error: {e}")
            return 1
    
    elif args.command == 'decrypt-value':
        password = args.password or getpass.getpass("Enter decryption password: ")
        if not password:
            print("❌ Password required")
            return 1
        
        try:
            decrypted = decrypt_api_key(args.value, password)
            print(f"Decrypted value:\n{decrypted}")
        except Exception as e:
            print(f"❌ Error: {e}")
            return 1
    
    elif args.command == 'generate-key':
        key = generate_key()
        print(f"Generated key:\n{key}")
        print("\nStore this key securely (e.g., in a password manager)")
    
    elif args.command == 'check':
        input_path = Path(args.input)
        if not input_path.exists():
            print(f"❌ File not found: {input_path}")
            return 1
        
        print(f"Checking {input_path}...")
        print("-" * 60)
        
        with open(input_path, 'r') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#') or '=' not in line:
                    continue
                
                key, value = line.split('=', 1)
                key = key.strip()
                
                if is_encrypted(value):
                    print(f"🔒 {key}: ENCRYPTED")
                elif any(s in key.upper() for s in ['KEY', 'SECRET', 'PASSWORD', 'PRIVATE', 'TOKEN']):
                    # Mask sensitive values
                    masked = value[:4] + '*' * (len(value) - 8) + value[-4:] if len(value) > 8 else '****'
                    print(f"⚠️  {key}: PLAIN ({masked})")
                else:
                    print(f"   {key}: plain")
    
    return 0


if __name__ == "__main__":
    exit(main() or 0)
