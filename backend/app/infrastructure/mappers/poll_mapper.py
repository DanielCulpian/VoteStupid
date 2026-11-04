from app.domain.entities.poll import Poll
from app.domain.entities.option import Option
from app.domain.entities.poll_type import PollType

from app.infrastructure.models.poll_model import PollModel
from app.infrastructure.models.option_model import OptionModel


def to_model(poll: Poll) -> PollModel:
    option_models = [
        OptionModel(
            id=option.id,
            text=option.text
        )
        for option in poll.options
    ]

    return PollModel(
        id=poll.id,
        title=poll.title,
        description=poll.description,
        poll_type=poll.poll_type.value,
        max_selections=poll.max_selections,
        closes_at=poll.closes_at,
        is_active=poll.is_active,
        created_at=poll.created_at,
        admin_token_hash=poll.admin_token_hash,
        options=option_models
    )


def to_entity(poll_model: PollModel) -> Poll:
    options = [
        Option(
            id=option.id,
            text=option.text
        )
        for option in poll_model.options
    ]

    return Poll(
        id=poll_model.id,
        title=poll_model.title,
        description=poll_model.description,
        poll_type=PollType(poll_model.poll_type),
        options=options,
        max_selections=poll_model.max_selections,
        closes_at=poll_model.closes_at,
        is_active=poll_model.is_active,
        admin_token_hash=poll_model.admin_token_hash,
        created_at=poll_model.created_at
    )