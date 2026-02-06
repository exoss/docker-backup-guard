import os
from cryptography.fernet import Fernet

# Store key in a persistent location (e.g., mapped volume)
KEY_FILE = "/backups/secret.key" 

def _get_key():
    """Loads or creates the encryption key."""
    if os.path.exists(KEY_FILE):
        try:
            with open(KEY_FILE, "rb") as f:
                return f.read()
        except Exception:
            pass # Fallback to generating new if unreadable (will break existing secrets)
    
    # Generate new key
    key = Fernet.generate_key()
    try:
        os.makedirs(os.path.dirname(KEY_FILE), exist_ok=True)
        with open(KEY_FILE, "wb") as f:
            f.write(key)
    except Exception as e:
        print(f"Warning: Could not save encryption key to {KEY_FILE}: {e}")
    return key

def encrypt_value(value):
    """Encrypts a string value."""
    if not value:
        return ""
    # If already encrypted, don't double encrypt
    if value.startswith("ENC("):
        return value
        
    try:
        f = Fernet(_get_key())
        token = f.encrypt(value.encode()).decode()
        return f"ENC({token})"
    except Exception as e:
        print(f"Encryption error: {e}")
        return value

def decrypt_value(value):
    """Decrypts a string value if it starts with ENC(."""
    if not value:
        return ""
    
    if value.startswith("ENC("):
        try:
            token = value[4:-1]
            f = Fernet(_get_key())
            return f.decrypt(token.encode()).decode()
        except Exception as e:
            print(f"Decryption error: {e}")
            return value # Return original on failure
            
    return value
