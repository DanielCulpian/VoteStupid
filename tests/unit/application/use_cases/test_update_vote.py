
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

from app.application.use_cases.update_vote import UpdateVote
from app.application.use_cases.validate_vote_selection import (
    ValidateVoteSelection
)
from app.domain.entities.option import Option
from app.domain.entities.poll import Poll
from app.domain.entities.poll_type import PollType
from app.domain.entities.vote import Vote
from app.domain.repositories.poll_repository import PollRepository


class FakePollRepository(PollRepository):

    def __init__(self):
        self.polls = {}
        self.votes = {}
        self.options = {}

    def get_by_id(self, poll_id):
        return self.polls.get(poll_id)

    def get_vote_by_voter(self, poll_id, voter_token_hash):
        return self.votes.get((poll_id, voter_token_hash))

    def save_vote(self, vote):
        self.votes[(vote.poll_id, vote.voter_token_hash)] = vote

    def update_vote(self, vote):
        self.votes[(vote.poll_id, vote.voter_token_hash)] = vote

    def get_options_by_ids(self, poll_id, option_ids):
        valid_options = self.options.get(poll_id, set())
        return [
            option_id
            for option_id in option_ids
            if option_id in valid_options
        ]

    def update_poll(self, poll: Poll) -> None:
        self.polls[poll.id] = poll

    def save_poll(self, poll):
        self.polls[poll.id] = poll

def create_poll(
    poll_type=PollType.SINGLE_CHOICE,
    max_selections=None,
    is_active=True,
    closes_at=None
):
    options = [
        Option(text="Opción 1"),
        Option(text="Opción 2"),
        Option(text="Opción 3")
    ]

    poll = Poll(
        title="Votación de prueba",
        poll_type=poll_type,
        options=options,
        max_selections=max_selections,
        is_active=is_active,
        closes_at=closes_at
    )

    return poll


def create_vote(poll, voter_token_hash="participant_hash"):
    return Vote(
        poll_id=poll.id,
        voter_token_hash=voter_token_hash,
        selected_option_ids=[poll.options[0].id]
    )


def create_use_case(repository):
    validator = ValidateVoteSelection(repository)

    return UpdateVote(
        poll_repository=repository,
        validate_vote_selection=validator
    )


def prepare_repository(poll, vote=None):
    repository = FakePollRepository()

    repository.polls[poll.id] = poll
    repository.options[poll.id] = {
        option.id for option in poll.options
    }

    if vote is not None:
        repository.save_vote(vote)

    return repository


# 1. Actualizar un voto correctamente

def test_update_vote_successfully():
    poll = create_poll()
    vote = create_vote(poll)

    repository = prepare_repository(poll, vote)
    use_case = create_use_case(repository)

    new_selection = [poll.options[1].id]

    updated_vote = use_case.execute(
        poll_id=poll.id,
        voter_token_hash=vote.voter_token_hash,
        selected_option_ids=new_selection
    )

    assert updated_vote.selected_option_ids == new_selection
    assert updated_vote.id == vote.id
    assert updated_vote.created_at == vote.created_at
    assert updated_vote.updated_at >= vote.updated_at


# 2. Rechazar una votación inexistente

def test_update_vote_rejects_nonexistent_poll():
    repository = FakePollRepository()
    use_case = create_use_case(repository)

    with pytest.raises(ValueError, match="La votación no existe"):
        use_case.execute(
            poll_id=uuid4(),
            voter_token_hash="participant_hash",
            selected_option_ids=[uuid4()]
        )


# 3. Rechazar una votación cerrada

def test_update_vote_rejects_closed_poll():
    poll = create_poll(is_active=False)
    vote = create_vote(poll)

    repository = prepare_repository(poll, vote)
    use_case = create_use_case(repository)

    with pytest.raises(ValueError, match="La votación está cerrada"):
        use_case.execute(
            poll_id=poll.id,
            voter_token_hash=vote.voter_token_hash,
            selected_option_ids=[poll.options[1].id]
        )


# 4. Rechazar una votación cuya fecha límite ha pasado

def test_update_vote_rejects_expired_poll():
    poll = create_poll(
        closes_at=datetime.now(timezone.utc) - timedelta(minutes=1)
    )
    vote = create_vote(poll)

    repository = prepare_repository(poll, vote)
    use_case = create_use_case(repository)

    with pytest.raises(
        ValueError,
        match="La votación ha alcanzado su fecha de cierre"
    ):
        use_case.execute(
            poll_id=poll.id,
            voter_token_hash=vote.voter_token_hash,
            selected_option_ids=[poll.options[1].id]
        )


# 5. Permitir actualizar antes de la fecha límite

def test_update_vote_allows_update_before_closing_date():
    poll = create_poll(
        closes_at=datetime.now(timezone.utc) + timedelta(hours=1)
    )
    vote = create_vote(poll)

    repository = prepare_repository(poll, vote)
    use_case = create_use_case(repository)

    new_selection = [poll.options[1].id]

    updated_vote = use_case.execute(
        poll_id=poll.id,
        voter_token_hash=vote.voter_token_hash,
        selected_option_ids=new_selection
    )

    assert updated_vote.selected_option_ids == new_selection


# 6. Rechazar la actualización si el participante no ha votado

def test_update_vote_rejects_participant_without_vote():
    poll = create_poll()

    repository = prepare_repository(poll)
    use_case = create_use_case(repository)

    with pytest.raises(
        ValueError,
        match="Este participante todavía no ha votado"
    ):
        use_case.execute(
            poll_id=poll.id,
            voter_token_hash="participant_hash",
            selected_option_ids=[poll.options[0].id]
        )


# 7. Rechazar una selección vacía

def test_update_vote_rejects_empty_selection():
    poll = create_poll()
    vote = create_vote(poll)

    repository = prepare_repository(poll, vote)
    use_case = create_use_case(repository)

    with pytest.raises(
        ValueError,
        match="Debes seleccionar al menos una opción"
    ):
        use_case.execute(
            poll_id=poll.id,
            voter_token_hash=vote.voter_token_hash,
            selected_option_ids=[]
        )


# 8. Rechazar opciones que no pertenecen a la votación

def test_update_vote_rejects_options_from_another_poll():
    poll = create_poll()
    other_poll = create_poll()
    vote = create_vote(poll)

    repository = prepare_repository(poll, vote)
    use_case = create_use_case(repository)

    with pytest.raises(
        ValueError,
        match="no pertenecen a esta votación"
    ):
        use_case.execute(
            poll_id=poll.id,
            voter_token_hash=vote.voter_token_hash,
            selected_option_ids=[other_poll.options[0].id]
        )


# 9. Rechazar opciones duplicadas

def test_update_vote_rejects_duplicate_options():
    poll = create_poll()
    vote = create_vote(poll)

    repository = prepare_repository(poll, vote)
    use_case = create_use_case(repository)

    with pytest.raises(
        ValueError,
        match="No puedes seleccionar una opción varias veces"
    ):
        use_case.execute(
            poll_id=poll.id,
            voter_token_hash=vote.voter_token_hash,
            selected_option_ids=[
                poll.options[0].id,
                poll.options[0].id
            ]
        )


# 10. Rechazar varias opciones en elección única

def test_update_vote_rejects_multiple_options_in_single_choice():
    poll = create_poll(PollType.SINGLE_CHOICE)
    vote = create_vote(poll)

    repository = prepare_repository(poll, vote)
    use_case = create_use_case(repository)

    with pytest.raises(
        ValueError,
        match="exactamente una opción"
    ):
        use_case.execute(
            poll_id=poll.id,
            voter_token_hash=vote.voter_token_hash,
            selected_option_ids=[
                poll.options[0].id,
                poll.options[1].id
            ]
        )


# 11. Rechazar superar el máximo de selección múltiple

def test_update_vote_rejects_exceeding_max_selections():
    poll = create_poll(
        PollType.MULTIPLE_CHOICE,
        max_selections=2
    )
    vote = create_vote(poll)

    repository = prepare_repository(poll, vote)
    use_case = create_use_case(repository)

    with pytest.raises(
        ValueError,
        match="No puedes seleccionar más de 2 opciones"
    ):
        use_case.execute(
            poll_id=poll.id,
            voter_token_hash=vote.voter_token_hash,
            selected_option_ids=[
                option.id for option in poll.options
            ]
        )


# 12. Permitir selección múltiple sin límite configurado

def test_update_vote_allows_multiple_choice_without_limit():
    poll = create_poll(PollType.MULTIPLE_CHOICE)
    vote = create_vote(poll)

    repository = prepare_repository(poll, vote)
    use_case = create_use_case(repository)

    new_selection = [
        option.id for option in poll.options
    ]

    updated_vote = use_case.execute(
        poll_id=poll.id,
        voter_token_hash=vote.voter_token_hash,
        selected_option_ids=new_selection
    )

    assert updated_vote.selected_option_ids == new_selection


# 13. Rechazar un ranking incompleto

def test_update_vote_rejects_incomplete_ranking():
    poll = create_poll(PollType.RANKING)
    vote = create_vote(poll)

    repository = prepare_repository(poll, vote)
    use_case = create_use_case(repository)

    with pytest.raises(
        ValueError,
        match="debes ordenar todas las opciones"
    ):
        use_case.execute(
            poll_id=poll.id,
            voter_token_hash=vote.voter_token_hash,
            selected_option_ids=[
                poll.options[0].id,
                poll.options[1].id
            ]
        )


# 14. Permitir un ranking completo

def test_update_vote_allows_complete_ranking():
    poll = create_poll(PollType.RANKING)
    vote = create_vote(poll)

    repository = prepare_repository(poll, vote)
    use_case = create_use_case(repository)

    new_selection = [
        poll.options[2].id,
        poll.options[0].id,
        poll.options[1].id
    ]

    updated_vote = use_case.execute(
        poll_id=poll.id,
        voter_token_hash=vote.voter_token_hash,
        selected_option_ids=new_selection
    )

    assert updated_vote.selected_option_ids == new_selection


# 15. Conservar la identidad y la fecha de creación del voto

def test_update_vote_preserves_original_vote_identity():
    poll = create_poll()
    vote = create_vote(poll)

    original_id = vote.id
    original_created_at = vote.created_at

    repository = prepare_repository(poll, vote)
    use_case = create_use_case(repository)

    updated_vote = use_case.execute(
        poll_id=poll.id,
        voter_token_hash=vote.voter_token_hash,
        selected_option_ids=[poll.options[1].id]
    )

    assert updated_vote.id == original_id
    assert updated_vote.created_at == original_created_at
    assert repository.get_vote_by_voter(
        poll.id,
        vote.voter_token_hash
    ) is updated_vote
