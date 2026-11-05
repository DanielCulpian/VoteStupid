from app.domain.vote_rule_error import VoteRuleError

from uuid import UUID
from datetime import datetime, timezone

from app.domain.entities.vote import Vote
from app.domain.repositories.poll_repository import PollRepository
from app.application.use_cases.validate_vote_selection import (
    ValidateVoteSelection
)


class UpdateVote:

    def __init__(
        self,
        poll_repository: PollRepository,
        validate_vote_selection: ValidateVoteSelection
    ):
        """Receive the dependencies required to execute the use case."""
        self.poll_repository = poll_repository
        self.validate_vote_selection = validate_vote_selection

    def execute(
        self,
        poll_id: UUID,
        voter_token_hash: str,
        selected_option_ids: list[UUID]
    ) -> Vote:
        """Validate the poll and selection before updating the participant's vote."""

        # 1. Retrieve the poll
        poll = self.poll_repository.get_by_id(poll_id)

        if poll is None:
            raise VoteRuleError("La votación no existe.")

        # 2. Check that the poll is open
        if not poll.is_active:
            raise VoteRuleError("La votación está cerrada.")

        # 3. Check the closing deadline
        if (
            poll.closes_at is not None
            and datetime.now(timezone.utc) >= poll.closes_at
        ):
            raise VoteRuleError("La votación ha alcanzado su fecha de cierre.")

        # 4. Find the existing vote
        existing_vote = self.poll_repository.get_vote_by_voter(
            poll_id,
            voter_token_hash
        )

        if existing_vote is None:
            raise VoteRuleError("Este participante todavía no ha votado.")

        # 5. Validate the new selection
        self.validate_vote_selection.execute(
            poll=poll,
            selected_option_ids=selected_option_ids
        )

        # 6. Update the vote
        existing_vote.update_selection(selected_option_ids)

        # 7. Save the changes
        self.poll_repository.update_vote(existing_vote)

        # 8. Return the updated vote
        return existing_vote
