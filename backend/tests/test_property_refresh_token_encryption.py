"""
Property-based test for refresh token encryption.

Feature: gmail-expense-tracker
Property 3: Refresh Token Encryption

**Validates: Requirements 2.3, 7.1**

For any refresh token stored in the database, the stored value should not 
equal the plaintext token (must be encrypted).
"""

import pytest
from hypothesis import given, strategies as st, settings

from app.auth.encryption import encrypt_refresh_token, decrypt_refresh_token


# Strategy for generating refresh tokens (simulating OAuth tokens)
refresh_token_strategy = st.text(
    alphabet=st.characters(min_codepoint=33, max_codepoint=126),
    min_size=20,
    max_size=200
)


@pytest.mark.property
@settings(max_examples=50)
@given(token=refresh_token_strategy)
def test_refresh_token_encryption_not_plaintext(token):
    """
    Property 3: Refresh Token Encryption
    
    **Validates: Requirements 2.3, 7.1**
    
    For any refresh token, the encrypted value should not equal the plaintext token.
    """
    # Encrypt the token
    encrypted = encrypt_refresh_token(token)
    
    # The encrypted token should not equal the plaintext
    assert encrypted != token, \
        "Encrypted token should not equal plaintext token"
    
    # The encrypted token should be a non-empty string
    assert isinstance(encrypted, str), \
        "Encrypted token should be a string"
    assert len(encrypted) > 0, \
        "Encrypted token should not be empty"


@pytest.mark.property
@settings(max_examples=50)
@given(token=refresh_token_strategy)
def test_refresh_token_encryption_decryption_roundtrip(token):
    """
    Property 3: Refresh Token Encryption (Roundtrip test)
    
    **Validates: Requirements 2.3, 7.1**
    
    For any refresh token, encrypting and then decrypting should return 
    the original token.
    """
    # Encrypt the token
    encrypted = encrypt_refresh_token(token)
    
    # Decrypt the token
    decrypted = decrypt_refresh_token(encrypted)
    
    # The decrypted token should equal the original
    assert decrypted == token, \
        f"Decrypted token should equal original. Expected: {token}, Got: {decrypted}"


@pytest.mark.property
@settings(max_examples=50)
@given(token1=refresh_token_strategy, token2=refresh_token_strategy)
def test_different_tokens_produce_different_encrypted_values(token1, token2):
    """
    Property 3: Refresh Token Encryption (Uniqueness test)
    
    **Validates: Requirements 2.3, 7.1**
    
    For any two different refresh tokens, their encrypted values should be different.
    """
    # Skip if tokens are the same
    if token1 == token2:
        return
    
    # Encrypt both tokens
    encrypted1 = encrypt_refresh_token(token1)
    encrypted2 = encrypt_refresh_token(token2)
    
    # The encrypted values should be different
    assert encrypted1 != encrypted2, \
        "Different tokens should produce different encrypted values"


@pytest.mark.property
def test_empty_token_raises_error():
    """
    Property 3: Refresh Token Encryption (Error handling)
    
    **Validates: Requirements 2.3, 7.1**
    
    Attempting to encrypt an empty token should raise a ValueError.
    """
    with pytest.raises(ValueError, match="Token cannot be empty"):
        encrypt_refresh_token("")


@pytest.mark.property
def test_empty_encrypted_token_raises_error():
    """
    Property 3: Refresh Token Encryption (Error handling)
    
    **Validates: Requirements 2.3, 7.1**
    
    Attempting to decrypt an empty encrypted token should raise a ValueError.
    """
    with pytest.raises(ValueError, match="Encrypted token cannot be empty"):
        decrypt_refresh_token("")
