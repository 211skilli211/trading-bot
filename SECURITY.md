# API Key Encryption for Trading Bot

This trading bot includes built-in encryption support to protect your API keys and secrets at rest.

## Overview

The security module uses **Fernet symmetric encryption** (from the `cryptography` library) to encrypt sensitive values in your `.env` file. Encrypted values are automatically decrypted when the bot starts.

## Features

- 🔐 **Strong Encryption**: Uses AES-128 in CBC mode with HMAC authentication (Fernet)
- 🔑 **Password-Based Keys**: Derives encryption keys using PBKDF2 with 480,000 iterations
- 🚀 **Auto-Decryption**: Bot automatically decrypts values on startup
- 🌐 **Dashboard Integration**: API endpoints for managing encryption via the web UI
- 📱 **CLI Tool**: Command-line interface for encrypting/decrypting

## Quick Start

### 1. Install Dependencies

```bash
pip install cryptography
```

Or use the existing requirements:
```bash
pip install -r requirements.txt
```

### 2. Check Current Security Status

```bash
python security.py check
```

This shows which API keys are encrypted vs plaintext.

### 3. Encrypt Your API Keys

```bash
# Encrypt all sensitive keys
python security.py encrypt -k BINANCE_API_KEY BINANCE_SECRET SOLANA_PRIVATE_KEY

# Or encrypt specific keys
python security.py encrypt -k BINANCE_API_KEY
```

You'll be prompted for a master password. Remember this password - you'll need it to decrypt!

### 4. Set Your Encryption Password

For automatic decryption when the bot starts:

```bash
export ENCRYPTION_PASSWORD="your-master-password"
```

Add this to your `~/.bashrc` or `~/.profile` to make it permanent.

### 5. Start the Bot

```bash
python launch_bot.py
```

The bot will automatically detect and decrypt encrypted values.

## CLI Commands

### Encrypt values in .env file
```bash
python security.py encrypt -k KEY1 KEY2 KEY3
```

Options:
- `--keys, -k`: Keys to encrypt (required)
- `--input, -i`: Input file (default: .env)
- `--output, -o`: Output file (default: overwrite input)
- `--password, -p`: Encryption password

### Decrypt values in .env file
```bash
python security.py decrypt
```

Options:
- `--input, -i`: Input file (default: .env)
- `--output, -o`: Output file (default: overwrite input)
- `--password, -p`: Decryption password

### Check encryption status
```bash
python security.py check
```

### Encrypt/decrypt single values
```bash
# Encrypt a single value
python security.py encrypt-value "my-secret-key"

# Decrypt a single value
python security.py decrypt-value "ENC:abc123:..."
```

### Generate a random encryption key
```bash
python security.py generate-key
```

## Encrypted Format

Encrypted values have this format:
```
ENC:<salt-base64>:<ciphertext-base64>
```

Example:
```env
BINANCE_API_KEY=ENC:7B8zTqR9xK2mN5pL:gAAAAABk...
BINANCE_SECRET=ENC:3WxYvBcE5fGhIjKl:gAAAAABk...
```

## Python API

### Load environment with auto-decryption

```python
from secure_env_loader import load_env

# Automatically decrypts if ENCRYPTION_PASSWORD is set
load_env(verbose=True)

# Or with explicit password
load_env(password="my-master-password")
```

### Manual encryption/decryption

```python
from security import encrypt_api_key, decrypt_api_key

# Encrypt
encrypted = encrypt_api_key("my-api-key", password="master-password")
print(encrypted)  # ENC:...:...

# Decrypt
decrypted = decrypt_api_key(encrypted, password="master-password")
print(decrypted)  # my-api-key
```

### Check if a value is encrypted

```python
from security import is_encrypted

if is_encrypted(os.getenv("BINANCE_API_KEY")):
    print("Key is encrypted")
```

### Encrypt/decrypt entire .env files

```python
from security import encrypt_env_file, decrypt_env_file

# Encrypt specific keys
encrypt_env_file(
    keys_to_encrypt=['BINANCE_API_KEY', 'BINANCE_SECRET'],
    password='master-password',
    input_path='.env',
    output_path='.env.encrypted'
)

# Decrypt all encrypted values
decrypt_env_file(
    password='master-password',
    input_path='.env',
    output_path='.env.decrypted'
)
```

## Dashboard API

When the dashboard is running, these endpoints are available:

### Check encryption status
```bash
curl http://localhost:8080/api/security/check
```

Response:
```json
{
  "success": true,
  "data": {
    "keys": {
      "BINANCE_API_KEY": {"encrypted": true, "set": true},
      "BINANCE_SECRET": {"encrypted": false, "set": true}
    },
    "stats": {
      "total_sensitive": 13,
      "configured": 8,
      "encrypted": 6,
      "plaintext": 2
    }
  }
}
```

### Encrypt via API
```bash
curl -X POST http://localhost:8080/api/security/encrypt \
  -H "Content-Type: application/json" \
  -d '{"password": "my-master-password", "keys": ["BINANCE_API_KEY"]}'
```

### Decrypt via API
```bash
curl -X POST http://localhost:8080/api/security/decrypt \
  -H "Content-Type: application/json" \
  -d '{"password": "my-master-password"}'
```

## Security Best Practices

1. **Use a strong master password** - At least 12 characters with mixed case, numbers, and symbols
2. **Don't commit .env files** - Already in .gitignore, but double-check
3. **Protect your master password** - Store in a password manager or environment variable
4. **Encrypt all sensitive keys** - Not just API keys, but also private keys and tokens
5. **Rotate keys periodically** - Change API keys every 90 days
6. **Use different passwords** - Don't reuse your encryption password elsewhere

## Troubleshooting

### "cryptography library not installed"
```bash
pip install cryptography
```

### "Decryption failed"
- Wrong master password
- Encrypted value was corrupted
- Salt was modified

### "No module named 'security'"
Make sure you're running from the trading-bot directory:
```bash
cd /root/trading-bot
python security.py check
```

### Values not auto-decrypting
- Check that `ENCRYPTION_PASSWORD` environment variable is set
- Verify the values have the `ENC:` prefix
- Run with verbose mode: `load_env(verbose=True)`

## Technical Details

### Encryption Algorithm
- **Cipher**: AES-128 in CBC mode
- **Authentication**: HMAC-SHA256
- **Key Derivation**: PBKDF2-HMAC-SHA256
- **Iterations**: 480,000 (OWASP recommended)
- **Salt Length**: 128 bits (16 bytes)

### Security Properties
- **Confidentiality**: Encrypted values cannot be read without the password
- **Integrity**: Tampered values will fail decryption
- **Unique salts**: Each encryption uses a random salt
- **Key stretching**: PBKDF2 makes brute-force attacks computationally expensive

## Migration Guide

### From plaintext .env

1. Backup your `.env` file:
   ```bash
   cp .env .env.backup
   ```

2. Encrypt sensitive values:
   ```bash
   python security.py encrypt -k BINANCE_API_KEY BINANCE_SECRET SOLANA_PRIVATE_KEY
   ```

3. Set your encryption password:
   ```bash
   export ENCRYPTION_PASSWORD="your-master-password"
   ```

4. Test the bot starts correctly:
   ```bash
   python launch_bot.py --mode paper
   ```

5. Delete the backup once confirmed working:
   ```bash
   rm .env.backup
   ```
