#!/usr/bin/env python3
"""
Security Utilities for Trading Bot
Handles credential sanitization, validation, and secure logging
"""

import os
import re
import hashlib
import logging
from typing import Optional


def sanitize_for_log(value: str, visible_chars: int = 4) -> str:
    """
    Sanitize sensitive values for logging.
    
    Args:
        value: The sensitive string to sanitize
        visible_chars: Number of characters to show at start/end
        
    Returns:
        Sanitized string like 'abcd****wxyz'
    """
    if not value or len(value) <= visible_chars * 2:
        return "****"
    return f"{value[:visible_chars]}****{value[-visible_chars:]}"


def mask_env_variables(text: str) -> str:
    """
    Mask all potential API keys/secrets in text.
    
    Args:
        text: Text that might contain sensitive data
        
    Returns:
        Text with sensitive values masked
    """
    # Patterns for common API key formats
    patterns = [
        (r'[a-zA-Z0-9]{32,}', '****'),
        (r'sk-[a-zA-Z0-9]{20,}', 'sk-****'),
        (r'Bearer\s+[a-zA-Z0-9\-_]+', 'Bearer ****'),
    ]
    
    result = text
    for pattern, replacement in patterns:
        result = re.sub(pattern, replacement, result)
    
    return result


def validate_config_value(name: str, value, expected_type, min_val=None, max_val=None, 
                          allowed_values=None) -> None:
    """
    Validate a configuration value.
    
    Args:
        name: Name of the config parameter
        value: The value to validate
        expected_type: Expected type (int, float, str, etc.)
        min_val: Minimum allowed value (for numeric)
        max_val: Maximum allowed value (for numeric)
        allowed_values: List of allowed values (for enums)
        
    Raises:
        ValueError: If validation fails
    """
    # Type check
    if not isinstance(value, expected_type):
        raise ValueError(f"{name} must be {expected_type.__name__}, got {type(value).__name__}")
    
    # Range check for numeric types
    if min_val is not None and value < min_val:
        raise ValueError(f"{name} must be >= {min_val}, got {value}")
    
    if max_val is not None and value > max_val:
        raise ValueError(f"{name} must be <= {max_val}, got {value}")
    
    # Enum check
    if allowed_values is not None and value not in allowed_values:
        raise ValueError(f"{name} must be one of {allowed_values}, got {value}")


def generate_idempotency_key(prefix: str = "BOT") -> str:
    """
    Generate a unique idempotency key for order execution.
    
    Args:
        prefix: Prefix for the key
        
    Returns:
        Unique string like "BOT_a1b2c3d4e5f6"
    """
    import uuid
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


def hash_sensitive_data(data: str) -> str:
    """
    Create a hash of sensitive data for comparison/logging.
    
    Args:
        data: Sensitive string to hash
        
    Returns:
        SHA-256 hash of the data
    """
    return hashlib.sha256(data.encode()).hexdigest()[:16]


class SecureLogger:
    """
    Logger wrapper that automatically sanitizes sensitive data.
    """
    
    SENSITIVE_KEYS = [
        'api_key', 'api_secret', 'secret', 'password', 'token',
        'private_key', 'mnemonic', 'seed', 'key', 'auth'
    ]
    
    def __init__(self, logger: logging.Logger):
        self.logger = logger
    
    def _sanitize_message(self, msg: str, extra: dict = None) -> tuple:
        """Sanitize message and extra data."""
        # Mask the message
        clean_msg = mask_env_variables(msg)
        
        # Sanitize extra dict if provided
        clean_extra = {}
        if extra:
            for key, value in extra.items():
                if any(sk in key.lower() for sk in self.SENSITIVE_KEYS):
                    clean_extra[key] = sanitize_for_log(str(value))
                else:
                    clean_extra[key] = value
        
        return clean_msg, clean_extra
    
    def debug(self, msg: str, *args, **kwargs):
        msg, kwargs['extra'] = self._sanitize_message(msg, kwargs.get('extra'))
        self.logger.debug(msg, *args, **kwargs)
    
    def info(self, msg: str, *args, **kwargs):
        msg, kwargs['extra'] = self._sanitize_message(msg, kwargs.get('extra'))
        self.logger.info(msg, *args, **kwargs)
    
    def warning(self, msg: str, *args, **kwargs):
        msg, kwargs['extra'] = self._sanitize_message(msg, kwargs.get('extra'))
        self.logger.warning(msg, *args, **kwargs)
    
    def error(self, msg: str, *args, **kwargs):
        msg, kwargs['extra'] = self._sanitize_message(msg, kwargs.get('extra'))
        self.logger.error(msg, *args, **kwargs)
    
    def critical(self, msg: str, *args, **kwargs):
        msg, kwargs['extra'] = self._sanitize_message(msg, kwargs.get('extra'))
        self.logger.critical(msg, *args, **kwargs)


def setup_secure_logging(name: str = "trading_bot", log_file: str = "bot.log", 
                         level: int = logging.INFO) -> SecureLogger:
    """
    Set up secure logging with sanitization.
    
    Args:
        name: Logger name
        log_file: Log file path
        level: Logging level
        
    Returns:
        SecureLogger instance
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # Clear existing handlers
    logger.handlers.clear()
    
    # Format
    formatter = logging.Formatter(
        '%(asctime)s [%(levelname)s] %(name)s: %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # File handler
    file_handler = logging.FileHandler(log_file)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    return SecureLogger(logger)


# Example usage
if __name__ == "__main__":
    print("Security Utils Test")
    print("=" * 60)
    
    # Test sanitization
    api_key = "abcdefghijklmnopqrstuvwxyz123456"
    print(f"\nOriginal: {api_key}")
    print(f"Sanitized: {sanitize_for_log(api_key)}")
    
    # Test masking
    text = "Error with key: sk-abc123xyz789 and token: bearer_12345abcdef"
    print(f"\nOriginal: {text}")
    print(f"Masked: {mask_env_variables(text)}")
    
    # Test validation
    print("\nValidation tests:")
    try:
        validate_config_value("stop_loss", 0.05, float, 0.001, 0.5)
        print("✓ stop_loss=0.05 is valid")
    except ValueError as e:
        print(f"✗ {e}")
    
    try:
        validate_config_value("stop_loss", 1.5, float, 0.001, 0.5)
        print("✓ stop_loss=1.5 is valid")
    except ValueError as e:
        print(f"✗ {e} (expected)")
    
    # Test idempotency key
    key = generate_idempotency_key()
    print(f"\nIdempotency key: {key}")
    
    # Test secure logging
    print("\nSecure logger test (check bot.log):")
    secure_log = setup_secure_logging("test", "test.log")
    secure_log.info("API Key loaded: sk-abc123def456ghi789")
    secure_log.info("Connected to exchange", extra={"api_key": "secret123456"})
    print("Check test.log for sanitized output")
