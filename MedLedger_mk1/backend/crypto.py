import os
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.backends import default_backend

private_key_pem = os.environ["RSA_PRIVATE_KEY"].encode().decode("unicode_escape").encode()
public_key_pem = os.environ["RSA_PUBLIC_KEY"].encode().decode("unicode_escape").encode()

private_key = serialization.load_pem_private_key(
    private_key_pem,
    password=None,
    backend=default_backend()
)

public_key = serialization.load_pem_public_key(
    public_key_pem,
    backend=default_backend()
)

def encrypt_text(plain_text: str) -> str:
    encrypted = public_key.encrypt(
        plain_text.encode(),
        padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None
        )
    )
    return encrypted.hex()

def decrypt_text(encrypted_hex: str) -> str:
    decrypted = private_key.decrypt(
        bytes.fromhex(encrypted_hex),
        padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None
        )
    )
    return decrypted.decode()
