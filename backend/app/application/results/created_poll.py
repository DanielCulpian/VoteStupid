from dataclasses import dataclass

from app.domain.entities.poll import Poll


@dataclass
class CreatedPoll:
    poll: Poll
    admin_token: str