
from abc import ABC, abstractmethod
from uuid import UUID

from app.domain.entities.poll import Poll
from app.domain.entities.vote import Vote


class PollRepository(ABC):

    @abstractmethod
    def get_by_id(self, poll_id: UUID) -> Poll | None:
        pass

    @abstractmethod
    def get_vote_by_voter(
        self,
        poll_id: UUID,
        voter_token_hash: str
    ) -> Vote | None:
        pass

    @abstractmethod
    def save_vote(self, vote: Vote) -> None:
        pass

    @abstractmethod
    def update_vote(self, vote: Vote) -> None:
        pass

    @abstractmethod
    def get_options_by_ids(
        self,
        poll_id: UUID,
        option_ids: list[UUID]
    ) -> list[UUID]:
        pass

    @abstractmethod
    def update_poll(self, poll: Poll) -> None:
        pass

    @abstractmethod
    def save_poll(self, poll: Poll) -> None:
        pass