from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization

def flatten_pem(pem_bytes: bytes) -> str:
    """
    Convert PEM byte string to a single-line string with `\\n` characters for .env usage.
    """
    return pem_bytes.decode().replace("\n", "\\n")

private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
public_key = private_key.public_key()

pem_private = private_key.private_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PrivateFormat.PKCS8,
    encryption_algorithm=serialization.NoEncryption()
)

pem_public = public_key.public_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PublicFormat.SubjectPublicKeyInfo
)

print(f'RSA_PRIVATE_KEY="{flatten_pem(pem_private)}"')
print(f'RSA_PUBLIC_KEY="{flatten_pem(pem_public)}"')
