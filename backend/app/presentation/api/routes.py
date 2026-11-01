from fastapi import APIRouter, Depends, status

from app.application.use_cases.create_poll import CreatePoll
from app.domain.entities.poll import Poll
from app.domain.repositories.poll_repository import PollRepository
from app.presentation.api.dependencies import get_poll_repository
from app.presentation.api.schemas import CreatePollRequest, PollResponse

router = APIRouter()


@router.get("/")
def home():
    return {
        "message": "¡Bienvenido a VoteStupid!"
    }


@router.get("/api/info")
def get_info():
    return {
        "app": "VoteStupid",
        "version": "0.1.0",
        "status": "En desarrollo",
        "description": "Aplicación de votaciones para amigos"
    }


@router.get("/api/status")
def get_status():
    return {
        "online": True,
        "message": "VoteStupid está funcionando"
    }

@router.post(
    "/api/polls",
    response_model=PollResponse,
    status_code=status.HTTP_201_CREATED
)
def create_poll(
    request: CreatePollRequest,
    poll_repository: PollRepository = Depends(get_poll_repository)
) -> Poll:
    use_case = CreatePoll(poll_repository)

    poll = use_case.execute(
        title=request.title,
        option_texts=request.option_texts,
        poll_type=request.poll_type,
        description=request.description,
        max_selections=request.max_selections,
        closes_at=request.closes_at
    )

    return poll