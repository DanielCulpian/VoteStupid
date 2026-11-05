from datetime import datetime, timezone
from uuid import UUID
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator, model_validator

from app.domain.entities.poll_type import PollType


class CreatePollRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=255)]
    option_texts: list[Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=255)]] = Field(min_length=2, max_length=50)
    poll_type: PollType
    description: Annotated[str, StringConstraints(strip_whitespace=True, max_length=5000)] | None = None
    max_selections: int | None = Field(default=None, ge=1, le=50, strict=True)
    closes_at: datetime | None = None

    @field_validator("title")
    @classmethod
    def validate_title(cls, value: str) -> str:
        """Trim the title and reject empty titles."""
        value = value.strip()

        if not value:
            raise ValueError("El título no puede estar vacío.")

        return value

    @field_validator("option_texts")
    @classmethod
    def validate_option_texts(cls, value: list[str]) -> list[str]:
        """Trim the option text and reject empty options."""
        cleaned_options = [option.strip() for option in value]

        if any(not option for option in cleaned_options):
            raise ValueError("Las opciones no pueden estar vacías.")

        return cleaned_options

    @field_validator("closes_at")
    @classmethod
    def validate_closes_at(cls, value: datetime | None) -> datetime | None:
        """Require a time zone when a closing date is provided."""
        if value is not None and (
            value.tzinfo is None or value.utcoffset() is None
        ):
            raise ValueError("La fecha de cierre debe incluir una zona horaria.")

        return value

    @model_validator(mode="after")
    def validate_max_selections(self):
        """Check that the selection limit is compatible with the poll type and options."""
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

    @model_validator(mode="after")
    def effective_status(self):
        """Present expired polls as closed without modifying the database."""
        if self.closes_at is not None and self.closes_at <= datetime.now(timezone.utc):
            self.is_active = False
        return self

class PollCreatedResponse(PollResponse):
    admin_token: str


class PollSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    title: str
    description: str | None
    poll_type: PollType
    created_at: datetime
    is_active: bool
    closes_at: datetime | None

    @model_validator(mode="after")
    def effective_status(self):
        """Keep the public state consistent with filters and voting restrictions."""
        if self.closes_at is not None and self.closes_at <= datetime.now(timezone.utc):
            self.is_active = False
        return self


class PollPage(BaseModel):
    items: list[PollSummary]
    total: int
    offset: int
    limit: int

class CastVoteRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    selected_option_ids: list[UUID] = Field(min_length=1, max_length=50)


class UpdateVoteRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    selected_option_ids: list[UUID] = Field(min_length=1, max_length=50)


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
