# backend/models.py

from pydantic import BaseModel
from typing import Optional

class Patient(BaseModel):
    name: str
    birthDate: str

class PatientCreate(Patient):
    username: str
    password: str

class UserLogin(BaseModel):
    username: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str

class PatientAdditional(BaseModel):
    gender: Optional[str]
    phone: Optional[str]
    email: Optional[str]
    address: Optional[str]
    emergencyContactName: Optional[str]
    emergencyContactPhone: Optional[str]