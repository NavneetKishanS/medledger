# backend/routes/users.py

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.security import OAuth2PasswordRequestForm
from auth import create_access_token
from models import Token

router = APIRouter()

# Hardcoded users (admin/doctor)
fake_users_db = {
    "bob": {"password": "secret2", "role": "doctor"},
    "carol": {"password": "secret3", "role": "admin"},
}

@router.post("/users/token", response_model=Token)
async def login_for_access_token(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends()
):
    username = form_data.username
    password = form_data.password

    print(f"[🔑] Login attempt for {username}")

    # 1️⃣ Check hardcoded users (admin/doctor)
    user = fake_users_db.get(username)
    if user:
        if user["password"] == password:
            access_token = create_access_token(
                data={"sub": username, "role": user["role"]}
            )
            print(f"[✅] Authenticated {username} (role={user['role']})")
            return {"access_token": access_token, "token_type": "bearer"}
        else:
            print(f"[❌] Wrong password for {username}")
            raise HTTPException(status_code=401, detail="Incorrect username or password")

    # 2️⃣ Otherwise check patients_basic collection
    db = request.app.state.mongo  # ⬅️ Reuse existing mongo client
    patient = await db["patients_basic"].find_one({"username": username})

    if not patient:
        print(f"[❌] No user {username} found in patients_basic")
        raise HTTPException(status_code=401, detail="Incorrect username or password")

    stored_password = patient.get("password")
    if not stored_password:
        print(f"[❌] No password stored for {username}")
        raise HTTPException(status_code=401, detail="Password missing")

    if password != stored_password:
        print(f"[❌] Password mismatch for {username}")
        raise HTTPException(status_code=401, detail="Incorrect username or password")

    access_token = create_access_token(
        data={"sub": username, "role": "patient"}
    )
    print(f"[✅] Patient {username} authenticated successfully!")
    return {"access_token": access_token, "token_type": "bearer"}
