from uuid import UUID

from app.domain.entities.poll import Poll
from app.domain.repositories.poll_repository import PollRepository


class ClosePoll:

    def __init__(self, poll_repository: PollRepository):
        """Receive the dependencies required to execute the use case."""
        self.poll_repository = poll_repository

    def execute(self, poll_id: UUID) -> Poll:
        """Mark the poll as closed and persist the change."""

        # 1. Find the poll
        poll = self.poll_repository.get_by_id(poll_id)

        # 2. Check whether the poll exists
        if poll is None:
            raise ValueError("La votación no existe.")

        # 3. Close the poll
        poll.is_active = False

        # 4. Save the changes
        self.poll_repository.update_poll(poll)

        # 5. Return the poll
        return poll