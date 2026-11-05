
from abc import ABC, abstractmethod
from uuid import UUID

from app.domain.entities.poll import Poll
from app.domain.entities.vote import Vote


class PollRepository(ABC):

    def list_polls(self, state: str, poll_type: str | None, offset: int, limit: int):
        """Query a paginated catalog without including votes or credentials."""
        raise NotImplementedError

    @abstractmethod
    def get_by_id(self, poll_id: UUID) -> Poll | None:
        """Retrieve a poll by its identifier, or return None if it does not exist."""
        pass

    @abstractmethod
    def get_vote_by_voter(
        self,
        poll_id: UUID,
        voter_token_hash: str
    ) -> Vote | None:
        """Find a participant's vote using the poll and the hash of their token."""
        pass

    @abstractmethod
    def save_vote(self, vote: Vote) -> None:
        """Persist a new vote with its selected options."""
        pass

    @abstractmethod
    def update_vote(self, vote: Vote) -> None:
        """Replace the existing vote selections and persist the modification timestamp."""
        pass

    @abstractmethod
    def get_options_by_ids(
        self,
        poll_id: UUID,
        option_ids: list[UUID]
    ) -> list[UUID]:
        """Return the requested identifiers that belong to the poll, in their original order."""
        pass

    @abstractmethod
    def update_poll(self, poll: Poll) -> None:
        """Define how a poll is updated in the repository."""
        pass

    @abstractmethod
    def save_poll(self, poll: Poll) -> None:
        """Persist a new poll and its options."""
        pass

    @abstractmethod
    def get_votes_by_poll(self, poll_id: UUID) -> list[Vote]:
        """Retrieve a poll's votes with their selections in order."""
        pass
