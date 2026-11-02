from uuid import UUID

from app.application.dto.poll_results import OptionResult, PollResults
from app.domain.entities.poll_type import PollType
from app.domain.repositories.poll_repository import PollRepository


class GetPollResults:

    def __init__(self, poll_repository: PollRepository):
        self.poll_repository = poll_repository

    def execute(self, poll_id: UUID) -> PollResults | None:
        poll = self.poll_repository.get_by_id(poll_id)

        if poll is None:
            return None

        votes = self.poll_repository.get_votes_by_poll(poll_id)
        total_votes = len(votes)

        option_results = []

        total_ranking_points = (
            total_votes * len(poll.options) * (len(poll.options) - 1) / 2
        )

        for option in poll.options:
            option_votes = sum(
                option.id in vote.selected_option_ids
                for vote in votes
            )

            points = 0

            if poll.poll_type == PollType.RANKING:
                for vote in votes:
                    position = vote.selected_option_ids.index(option.id)
                    points += len(poll.options) - position - 1
            else:
                points = option_votes

            if poll.poll_type == PollType.RANKING:
                percentage = (
                    points / total_ranking_points * 100
                    if total_ranking_points > 0
                    else 0.0
                )
            else:
                percentage = (
                    option_votes / total_votes * 100
                    if total_votes > 0
                    else 0.0
                )

            option_results.append(
                OptionResult(
                    option_id=option.id,
                    option_text=option.text,
                    votes=option_votes,
                    points=points,
                    percentage=percentage,
                )
            )

        return PollResults(
            poll_id=poll.id,
            poll_title=poll.title,
            total_votes=total_votes,
            results=option_results,
        )