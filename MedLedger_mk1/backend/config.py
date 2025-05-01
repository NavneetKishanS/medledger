import os
from dotenv import load_dotenv

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
MONGO_DB = os.getenv("MONGO_DB", "medledger_analytics")

FHIR_SERVER_URL = os.getenv("FHIR_SERVER_URL", "http://localhost:8080/fhir").rstrip("/")

JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "supersecretkey")
JWT_ALGORITHM = "HS256"
TOKEN_EXPIRATION_TIME = int(os.getenv("TOKEN_EXPIRATION_TIME", "60"))  # minutes

USERNAME_SYSTEM = "http://medledger.example.org/username"

BLOCKCHAIN_NODE_URL = os.getenv("BLOCKCHAIN_NODE_URL")
CONTRACT_ADDRESS = os.getenv("CONTRACT_ADDRESS")
PRIVATE_KEY = os.getenv("PRIVATE_KEY")

RSA_PRIVATE_KEY = os.getenv("RSA_PRIVATE_KEY")
RSA_PUBLIC_KEY = os.getenv("RSA_PUBLIC_KEY")
