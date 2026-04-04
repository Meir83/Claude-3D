import re
from datetime import datetime
from pydantic import BaseModel, field_validator, Field

UUID4_RE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$")


class ChatRequest(BaseModel):
    session_id: str = Field(..., description="UUID4 session identifier")
    message: str = Field(..., min_length=1, max_length=8000)

    @field_validator("session_id")
    @classmethod
    def validate_session_id(cls, v: str) -> str:
        if not UUID4_RE.match(v):
            raise ValueError("session_id must be a valid UUID4")
        return v


class MessageOut(BaseModel):
    id: int
    session_id: str
    role: str
    content: str
    created_at: datetime

    model_config = {"from_attributes": True}


class SessionOut(BaseModel):
    id: str
    title: str | None
    created_at: datetime
    updated_at: datetime
    messages: list[MessageOut] = []

    model_config = {"from_attributes": True}
