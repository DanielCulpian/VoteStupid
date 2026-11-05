from uuid import UUID
from datetime import datetime, timezone

from app.domain.entities.poll import Poll
from app.domain.repositories.poll_repository import PollRepository


class ReopenPoll:

    def __init__(self, poll_repository: PollRepository):
        """Receive the dependencies required to execute the use case."""
        self.poll_repository = poll_repository

    def execute(self, poll_id: UUID) -> Poll:
        """Mark the poll as open and persist the change."""

        # 1. Find the poll
        poll = self.poll_repository.get_by_id(poll_id)

        # 2. Check whether the poll exists
        if poll is None:
            raise ValueError("La votación no existe.")

        # 3. Reopen the poll
        poll.is_active = True
        # Explicitly reopening a poll removes an expired deadline so voting can resume.
        if poll.closes_at is not None and poll.closes_at <= datetime.now(timezone.utc):
            poll.closes_at = None

        # 4. Save the changes
        self.poll_repository.update_poll(poll)

        # 5. Return the poll
        return poll
