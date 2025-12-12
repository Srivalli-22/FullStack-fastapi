from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime


# ===========================
# USER SCHEMAS
# ===========================

class UserCreate(BaseModel):
    full_name: str
    email: EmailStr
    password: str


class UserOut(BaseModel):
    id: str
    full_name: str
    email: EmailStr
    role: str
    
    class Config:
        orm_mode = True


class Token(BaseModel):
    access_token: str
    token_type: str


# ===========================
# SHIPMENT SCHEMAS
# ===========================

class ShipmentCreate(BaseModel):
    shipment_number: str
    container_number: Optional[str] = None
    route: Optional[str] = None
    goods_type: Optional[str] = None
    device_id: Optional[str] = None
    expected_delivery: Optional[str] = None
    po_number: Optional[str] = None
    delivery_number: Optional[str] = None
    ndc_number: Optional[str] = None
    batch_id: Optional[str] = None
    serial_number: Optional[str] = None
    description: Optional[str] = None


class ShipmentOut(ShipmentCreate):
    id: str
    owner_id: Optional[str]
    created_at: Optional[datetime]

    class Config:
        orm_mode = True


# ===========================
# DEVICE EVENT SCHEMAS
# ===========================

# Request body (input from Swagger)
class DeviceEvent(BaseModel):
    device_id: str
    shipment_id: Optional[str] = None
    temperature: Optional[float] = None
    humidity: Optional[float] = None
    battery: Optional[float] = None
    status: Optional[str] = None
    message: Optional[str] = None
    route_from: Optional[str] = None
    route_to: Optional[str] = None


# MongoDB or SQL output (if needed)
class DeviceEventOut(BaseModel):
    id: str
    device_id: str
    battery: float
    temperature: str
    route_from: Optional[str]
    route_to: Optional[str]
    timestamp: datetime

    class Config:
        orm_mode = True
