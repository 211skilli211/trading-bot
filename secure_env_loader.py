#!/usr/bin/env python3
"""
Secure Environment Loader
=========================
Drop-in replacement for python-dotenv that supports automatic decryption.

This module provides a simple way to load environment variables with
automatic decryption support. Use this instead of direct dotenv loading.

Usage:
    # At the start of your main script (before importing other modules)
    from secure_env_loader import load_env
    load_env()  # Automatically decrypts if ENCRYPTION_PASSWORD is set
    
    # Or with explicit password
    load_env(password="my-master-password")
"""

import os
import sys
from pathlib import Path

# Try to import the security module
try:
    from security import load_encrypted_env, CRYPTO_AVAILABLE
except ImportError:
    CRYPTO_AVAILABLE = False
    load_encrypted_env = None

# Try to import dotenv as fallback
try:
    from dotenv import load_dotenv
    DOTENV_AVAILABLE = True
except ImportError:
    DOTENV_AVAILABLE = False
    load_dotenv = None


def load_env(
    dotenv_path: str = ".env",
    password: str = None,
    password_env_var: str = "ENCRYPTION_PASSWORD",
    override: bool = True,
    verbose: bool = False
) -> dict:
    """
    Load environment variables with automatic decryption support.
    
    This is a drop-in replacement for load_dotenv() that automatically
    handles encrypted values in the .env file.
    
    Args:
        dotenv_path: Path to .env file (default: .env in current directory)
        password: Master password for decryption (if None, reads from password_env_var)
        password_env_var: Environment variable name containing the password
        override: Whether to override existing environment variables
        verbose: Whether to print status messages
        
    Returns:
        Dictionary of loaded environment variables
        
    Example:
        >>> from secure_env_loader import load_env
        >>> load_env()
        >>> print(os.getenv('BINANCE_API_KEY'))  # Auto-decrypted if encrypted
    """
    dotenv_path = Path(dotenv_path)
    
    if not dotenv_path.exists():
        if verbose:
            print(f"[SecureEnv] Warning: {dotenv_path} not found")
        return {}
    
    # Check if file contains encrypted values
    has_encrypted = False
    try:
        with open(dotenv_path, 'r') as f:
            content = f.read()
            has_encrypted = 'ENC:' in content
    except Exception:
        pass
    
    # Use encrypted loader if available and needed
    if CRYPTO_AVAILABLE and DOTENV_AVAILABLE:
        if has_encrypted and verbose:
            print(f"[SecureEnv] Detected encrypted values in {dotenv_path}")
        
        # Load with decryption support
        env_vars = load_encrypted_env(
            dotenv_path=str(dotenv_path),
            password=password,
            password_env_var=password_env_var
        )
        
        if verbose:
            encrypted_count = sum(
                1 for v in env_vars.values()
                if isinstance(v, str) and v.startswith('ENC:')
            )
            if encrypted_count > 0:
                print(f"[SecureEnv] Loaded {len(env_vars)} vars ({encrypted_count} encrypted)")
            else:
                print(f"[SecureEnv] Loaded {len(env_vars)} vars")
        
        return env_vars
    
    # Fallback to regular dotenv
    elif DOTENV_AVAILABLE:
        if has_encrypted:
            print(f"[SecureEnv] Warning: {dotenv_path} contains encrypted values but cryptography is not installed")
            print("[SecureEnv] Install with: pip install cryptography")
        
        load_dotenv(dotenv_path, override=override)
        
        if verbose:
            print(f"[SecureEnv] Loaded {dotenv_path} (no encryption support)")
        
        return dict(os.environ)
    
    else:
        if verbose:
            print("[SecureEnv] Warning: python-dotenv not installed, cannot load .env file")
        return {}


def get_decrypted(key: str, default: str = None, password: str = None) -> str:
    """
    Get a decrypted environment variable value.
    
    This is useful for retrieving encrypted values that weren't decrypted
    during load_env() (e.g., if ENCRYPTION_PASSWORD wasn't set).
    
    Args:
        key: Environment variable name
        default: Default value if not found
        password: Master password for decryption (if needed)
        
    Returns:
        Decrypted value or default
    """
    value = os.getenv(key, default)
    
    if value and value.startswith('ENC:') and CRYPTO_AVAILABLE and password:
        try:
            from security import decrypt_api_key
            return decrypt_api_key(value, password)
        except Exception as e:
            print(f"[SecureEnv] Failed to decrypt {key}: {e}")
    
    return value


def init_bot_with_security(config_path: str = "config.json", verbose: bool = True):
    """
    Initialize the trading bot with security features enabled.
    
    This function:
    1. Loads the .env file with automatic decryption
    2. Validates that required API keys are available
    3. Warns about unencrypted sensitive values
    
    Args:
        config_path: Path to bot configuration file
        verbose: Whether to print status messages
        
    Returns:
        Tuple of (config_dict, security_status_dict)
    """
    import json
    
    # Load environment with decryption
    env_vars = load_env(verbose=verbose)
    
    # Check for sensitive values
    sensitive_keys = [
        'BINANCE_API_KEY', 'BINANCE_SECRET',
        'COINBASE_API_KEY', 'COINBASE_SECRET',
        'KRAKEN_API_KEY', 'KRAKEN_SECRET',
        'BYBIT_API_KEY', 'BYBIT_SECRET',
        'KUCOIN_API_KEY', 'KUCOIN_SECRET', 'KUCOIN_PASSPHRASE',
        'SOLANA_PRIVATE_KEY',
        'TELEGRAM_BOT_TOKEN'
    ]
    
    security_status = {
        "encrypted_count": 0,
        "plaintext_count": 0,
        "missing_count": 0,
        "warnings": []
    }
    
    for key in sensitive_keys:
        value = os.getenv(key)
        if not value or value.startswith('your_'):
            security_status["missing_count"] += 1
        elif value.startswith('ENC:'):
            security_status["encrypted_count"] += 1
        else:
            security_status["plaintext_count"] += 1
            security_status["warnings"].append(
                f"{key} is stored in plaintext - consider encrypting with: python security.py encrypt -k {key}"
            )
    
    # Print warnings
    if verbose and security_status["warnings"]:
        print("\n[SecureEnv] Security Recommendations:")
        for warning in security_status["warnings"]:
            print(f"  ⚠️  {warning}")
        print()
    
    # Load config
    config = {}
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
    except FileNotFoundError:
        if verbose:
            print(f"[SecureEnv] Config file not found: {config_path}")
    except json.JSONDecodeError as e:
        if verbose:
            print(f"[SecureEnv] Invalid JSON in {config_path}: {e}")
    
    if verbose:
        print(f"[SecureEnv] Security Status: {security_status['encrypted_count']} encrypted, "
              f"{security_status['plaintext_count']} plaintext, "
              f"{security_status['missing_count']} missing")
    
    return config, security_status


# Auto-load on import if SECURE_ENV_AUTOLOAD is set
if os.getenv('SECURE_ENV_AUTOLOAD', 'false').lower() in ('true', '1', 'yes'):
    load_env(verbose=True)
