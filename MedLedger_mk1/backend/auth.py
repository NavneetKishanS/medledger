
import jwt
from datetime import datetime, timedelta
from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
import config

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="users/token")


def create_access_token(data: dict) -> str:
    """
    Create a JWT token embedding whatever is in 'data' (e.g. sub=username, role=...),
    signed with our secret, and expiring after TOKEN_EXPIRATION_TIME minutes.
    """
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=config.TOKEN_EXPIRATION_TIME)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, config.JWT_SECRET_KEY, algorithm=config.JWT_ALGORITHM)


def get_current_user(token: str = Depends(oauth2_scheme)) -> dict:
    """
    Decode the incoming JWT, verify its signature and expiry, and return
    a dict with at least 'username' and 'role'. Raises 401 if invalid.
    """
    try:
        payload = jwt.decode(token, config.JWT_SECRET_KEY, algorithms=[config.JWT_ALGORITHM])
        username: str = payload.get("sub")
        role: str = payload.get("role")
        if not username or not role:
            raise HTTPException(status_code=401, detail="Invalid token payload")
        return {"username": username, "role": role}
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
