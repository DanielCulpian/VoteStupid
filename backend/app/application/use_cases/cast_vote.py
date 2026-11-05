from app.domain.vote_rule_error import VoteRuleError

from uuid import UUID
from datetime import datetime, timezone

from app.domain.entities.vote import Vote
from app.domain.repositories.poll_repository import PollRepository
from app.application.use_cases.validate_vote_selection import (
    ValidateVoteSelection
)


class CastVote:

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
        """Validate the poll state, voter, and selection before saving a new vote."""

        # 1. Retrieve the poll
        poll = self.poll_repository.get_by_id(poll_id)

        if poll is None:
            raise VoteRuleError("La votación no existe.")

        # 2. Check that the poll is open
        if not poll.is_active:
            raise VoteRuleError("La votación está cerrada.")

        # 2.1 Check that the closing deadline has not been reached
        if (
            poll.closes_at is not None
            and datetime.now(timezone.utc) >= poll.closes_at
        ):
            raise VoteRuleError("La votación ha alcanzado su fecha de cierre.")

        # 3. Check that the voter has not already voted
        existing_vote = self.poll_repository.get_vote_by_voter(
            poll_id,
            voter_token_hash
        )

        if existing_vote is not None:
            raise VoteRuleError("Este participante ya ha votado.")

        # 4. Validate the selection
        self.validate_vote_selection.execute(
            poll=poll,
            selected_option_ids=selected_option_ids
        )

        # 5. Create the vote
        vote = Vote(
            poll_id=poll_id,
            voter_token_hash=voter_token_hash,
            selected_option_ids=selected_option_ids
        )

        # 6. Save the vote
        self.poll_repository.save_vote(vote)

        # 7. Return the created vote
        return vote
