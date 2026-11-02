from dataclasses import dataclass
from uuid import UUID


@dataclass
class OptionResult:
    option_id: UUID
    option_text: str
    votes: int
    points: int
    percentage: float


@dataclass
class PollResults:
    poll_id: UUID
    poll_title: str
    total_votes: int
    results: list[OptionResult]