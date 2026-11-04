from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.domain.entities.poll_type import PollType


class CreatePollRequest(BaseModel):
    title: str
    option_texts: list[str] = Field(min_length=2)
    poll_type: PollType
    description: str | None = None
    max_selections: int | None = Field(default=None, ge=1)
    closes_at: datetime | None = None

    @field_validator("title")
    @classmethod
    def validate_title(cls, value: str) -> str:
        value = value.strip()

        if not value:
            raise ValueError("El título no puede estar vacío.")

        return value

    @field_validator("option_texts")
    @classmethod
    def validate_option_texts(cls, value: list[str]) -> list[str]:
        cleaned_options = [option.strip() for option in value]

        if any(not option for option in cleaned_options):
            raise ValueError("Las opciones no pueden estar vacías.")

        return cleaned_options

    @field_validator("closes_at")
    @classmethod
    def validate_closes_at(cls, value: datetime | None) -> datetime | None:
        if value is not None and (
            value.tzinfo is None or value.utcoffset() is None
        ):
            raise ValueError("La fecha de cierre debe incluir una zona horaria.")

        return value

    @model_validator(mode="after")
    def validate_max_selections(self):
        if self.poll_type != PollType.MULTIPLE_CHOICE:
            if self.max_selections is not None:
                raise ValueError(
                    "max_selections solo se puede utilizar en selección múltiple."
                )

        elif self.max_selections is not None:
            if self.max_selections > len(self.option_texts):
                raise ValueError(
                    "El máximo de selecciones no puede superar el número de opciones."
                )

        return self


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

class PollCreatedResponse(PollResponse):
    admin_token: str

class CastVoteRequest(BaseModel):
    selected_option_ids: list[UUID] = Field(min_length=1)


class UpdateVoteRequest(BaseModel):
    selected_option_ids: list[UUID] = Field(min_length=1)


class VoteResponse(BaseModel):
    id: UUID
    poll_id: UUID
    selected_option_ids: list[UUID]
    created_at: datetime
    updated_at: datetime

class OptionResultResponse(BaseModel):
    option_id: UUID
    option_text: str
    votes: int
    points: int
    percentage: float


class PollResultsResponse(BaseModel):
    poll_id: UUID
    poll_title: str
    total_votes: int
    results: list[OptionResultResponse]