from datetime import datetime

from app.domain.entities.option import Option
from app.domain.entities.poll import Poll
from app.domain.entities.poll_type import PollType
from app.domain.repositories.poll_repository import PollRepository

from app.application.results.created_poll import CreatedPoll
from app.infrastructure.security.admin_token import (
    generate_admin_token,
    hash_admin_token,
)


class CreatePoll:

    def __init__(self, poll_repository: PollRepository):
        """Receive the dependencies required to execute the use case."""
        self.poll_repository = poll_repository

    def execute(
        self,
        title: str,
        option_texts: list[str],
        poll_type: PollType,
        description: str | None = None,
        max_selections: int | None = None,
        closes_at: datetime | None = None
    ) -> CreatedPoll:
        """Create and persist a poll, returning its private administration token."""

        # 1. Generate the administration secret.
        admin_token = generate_admin_token()

        # 2. Create the options.
        options = [
            Option(text=option_text)
            for option_text in option_texts
        ]

        # 3. Create the poll with the hashed secret.
        poll = Poll(
            title=title,
            poll_type=poll_type,
            options=options,
            description=description,
            max_selections=max_selections,
            closes_at=closes_at,
            admin_token_hash=hash_admin_token(admin_token),
        )

        # 4. Save the poll.
        self.poll_repository.save_poll(poll)

        # 5. Return the poll and the original secret.
        return CreatedPoll(
            poll=poll,
            admin_token=admin_token,
        )