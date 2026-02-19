"""
Encryption utilities for securing sensitive data.

This module provides Fernet-based encryption for refresh tokens and other
sensitive data that needs to be stored in the database.
"""

import os
from cryptography.fernet import Fernet


def get_encryption_key() -> bytes:
    """
    Get the encryption key from environment variable.
    
    Returns:
        bytes: The encryption key for Fernet cipher.
        
    Raises:
        ValueError: If ENCRYPTION_KEY environment variable is not set.
    """
    key = os.getenv("ENCRYPTION_KEY")
    if not key:
        raise ValueError("ENCRYPTION_KEY environment variable is not set")
    
    # Ensure the key is in bytes format
    if isinstance(key, str):
        key = key.encode()
    
    return key


def encrypt_refresh_token(token: str) -> str:
    """
    Encrypt a refresh token using Fernet symmetric encryption.
    
    Args:
        token: The plaintext refresh token to encrypt.
        
    Returns:
        str: The encrypted token as a base64-encoded string.
        
    Raises:
        ValueError: If the token is empty or encryption key is invalid.
    """
    if not token:
        raise ValueError("Token cannot be empty")
    
    encryption_key = get_encryption_key()
    fernet = Fernet(encryption_key)
    
    # Encrypt the token
    encrypted_bytes = fernet.encrypt(token.encode())
    
    # Return as string for database storage
    return encrypted_bytes.decode()


def decrypt_refresh_token(encrypted_token: str) -> str:
    """
    Decrypt an encrypted refresh token.
    
    Args:
        encrypted_token: The encrypted token as a base64-encoded string.
        
    Returns:
        str: The decrypted plaintext token.
        
    Raises:
        ValueError: If the encrypted token is empty or invalid.
        cryptography.fernet.InvalidToken: If decryption fails.
    """
    if not encrypted_token:
        raise ValueError("Encrypted token cannot be empty")
    
    encryption_key = get_encryption_key()
    fernet = Fernet(encryption_key)
    
    # Decrypt the token
    decrypted_bytes = fernet.decrypt(encrypted_token.encode())
    
    # Return as string
    return decrypted_bytes.decode()
