import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


# ───── Auth ─────
class UserRegister(BaseModel):
    email: EmailStr
    password: str
    full_name: str


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    id: uuid.UUID
    email: str
    full_name: str
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


# ───── Templates ─────
class TemplateOut(BaseModel):
    id: uuid.UUID
    name: str
    slug: str
    description: str | None
    template_schema: dict = Field(alias="schema")

    model_config = {
        "from_attributes": True,
        "populate_by_name": True,
    }


class TemplateListItem(BaseModel):
    id: uuid.UUID
    name: str
    slug: str
    description: str | None

    model_config = {"from_attributes": True}


# ───── Requests ─────
class DocumentRequestCreate(BaseModel):
    template_slug: str
    input_data: dict
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "template_slug": "invoice",
                "input_data": {
                    "invoice_num": "INV-001",
                    "amount": 50000
                }
            }
        }
    }


class DocumentRequestFromText(BaseModel):
    template_slug: str
    text: str

    model_config = {
        "json_schema_extra": {
            "example": {
                "template_slug": " ",
                "text": " ",
            }
        }
    }


class DocumentRequestOut(BaseModel):
    id: uuid.UUID
    template_id: uuid.UUID
    status: str
    file_path: str | None
    error_message: str | None
    created_at: datetime
    started_at: datetime | None
    completed_at: datetime | None

    model_config = {"from_attributes": True}
