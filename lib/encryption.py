"""
Encryption utilities for securely storing API keys in cookies.
Based on the mobile PWA encryption system.
"""
import os
import base64
import hashlib
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import padding


class Encryption:
    """Handle AES-256-CBC encryption for API keys"""
    
    def __init__(self, encryption_key: str):
        """
        Initialize encryption with a key.
        
        Args:
            encryption_key: 32-character hex string (16 bytes when decoded)
        """
        if len(encryption_key) != 32:
            raise ValueError("Encryption key must be 32 characters (16 bytes hex)")
        self.key = bytes.fromhex(encryption_key)
    
    def encrypt(self, plaintext: str) -> str:
        """
        Encrypt a string using AES-256-CBC.
        
        Args:
            plaintext: String to encrypt (e.g., API key)
            
        Returns:
            Base64-encoded string containing IV and ciphertext
        """
        # Generate random IV
        iv = os.urandom(16)
        
        # Pad the plaintext
        padder = padding.PKCS7(128).padder()
        padded_data = padder.update(plaintext.encode('utf-8')) + padder.finalize()
        
        # Encrypt
        cipher = Cipher(
            algorithms.AES(self.key),
            modes.CBC(iv),
            backend=default_backend()
        )
        encryptor = cipher.encryptor()
        ciphertext = encryptor.update(padded_data) + encryptor.finalize()
        
        # Combine IV and ciphertext, then base64 encode
        combined = iv + ciphertext
        return base64.b64encode(combined).decode('utf-8')
    
    def decrypt(self, encrypted: str) -> str:
        """
        Decrypt an encrypted string.
        
        Args:
            encrypted: Base64-encoded string containing IV and ciphertext
            
        Returns:
            Decrypted plaintext string
        """
        try:
            # Decode from base64
            combined = base64.b64decode(encrypted)
            
            # Extract IV and ciphertext
            iv = combined[:16]
            ciphertext = combined[16:]
            
            # Decrypt
            cipher = Cipher(
                algorithms.AES(self.key),
                modes.CBC(iv),
                backend=default_backend()
            )
            decryptor = cipher.decryptor()
            padded_plaintext = decryptor.update(ciphertext) + decryptor.finalize()
            
            # Unpad
            unpadder = padding.PKCS7(128).unpadder()
            plaintext = unpadder.update(padded_plaintext) + unpadder.finalize()
            
            return plaintext.decode('utf-8')
        except Exception as e:
            raise ValueError(f"Decryption failed: {str(e)}")
    
    @staticmethod
    def hash_api_key(api_key: str) -> str:
        """
        Create a hash of the API key for use as database filename.
        
        Args:
            api_key: The API key to hash
            
        Returns:
            Hex string of the hash (safe for filenames)
        """
        return hashlib.sha256(api_key.encode('utf-8')).hexdigest()[:16]
    
    @staticmethod
    def validate_api_key_format(api_key: str) -> bool:
        """
        Validate that an API key matches the expected format.
        
        Args:
            api_key: The API key to validate
            
        Returns:
            True if format is valid, False otherwise
        """
        # Slide API keys start with tk_ and are alphanumeric with underscores
        if not api_key or not isinstance(api_key, str):
            return False
        
        if not api_key.startswith('tk_'):
            return False
        
        if len(api_key) < 10:
            return False
        
        # Check if it contains only valid characters
        valid_chars = set('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_')
        return all(c in valid_chars for c in api_key)

