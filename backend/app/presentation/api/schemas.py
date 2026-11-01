from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.domain.entities.poll_type import PollType


class CreatePollRequest(BaseModel):
    title: str
    option_texts: list[str]
    poll_type: PollType
    description: str | None = None
    max_selections: int | None = None
    closes_at: datetime | None = None


class OptionResponse(BaseModel):
    id: UUID
    text: str

    model_config = ConfigDict(from_attributes=True)


class PollResponse(BaseModel):
    id: UUID
    title: str
    description: str | None
    poll_type: PollType
    options: list[OptionResponse]
    max_selections: int | None
    closes_at: datetime | None
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)