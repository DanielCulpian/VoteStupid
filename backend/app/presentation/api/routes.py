from fastapi import (
    APIRouter,
    Depends,
    status,
    HTTPException,
    Header,
    WebSocket,
    WebSocketDisconnect,
)
from app.infrastructure.realtime.connection_manager import connection_manager
from app.application.use_cases.create_poll import CreatePoll
from app.domain.entities.poll import Poll
from app.domain.repositories.poll_repository import PollRepository
from app.presentation.api.dependencies import get_poll_repository, get_cast_vote_use_case, get_update_vote_use_case, get_poll_results_use_case
from app.presentation.api.schemas import CreatePollRequest, PollResponse, CastVoteRequest, VoteResponse, UpdateVoteRequest
from app.application.use_cases.cast_vote import CastVote
from app.infrastructure.security.voter_token import hash_voter_token
from app.application.use_cases.update_vote import UpdateVote
from app.application.use_cases.get_poll_results import GetPollResults
from app.presentation.api.schemas import PollResultsResponse
from uuid import UUID

from app.application.use_cases.get_poll import GetPoll

router = APIRouter()

def build_results_message(results: PollResultsResponse) -> dict:
    return {
        "type": "results_updated",
        "results": results.model_dump(mode="json"),
    }

@router.get("/")
def home():
    return {
        "message": "Â¡Bienvenido a VoteStupid!"
    }


@router.get("/api/info")
def get_info():
    return {
        "app": "VoteStupid",
        "version": "0.1.0",
        "status": "En desarrollo",
        "description": "AplicaciÃ³n de votaciones para amigos"
    }


@router.get("/api/status")
def get_status():
    return {
        "online": True,
        "message": "VoteStupid estÃ¡ funcionando"
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

@router.get(
    "/api/polls/{poll_id}",
    response_model=PollResponse
)
def get_poll(
    poll_id: UUID,
    poll_repository: PollRepository = Depends(get_poll_repository)
) -> Poll:
    use_case = GetPoll(poll_repository)

    poll = use_case.execute(poll_id)

    if poll is None:
        raise HTTPException(
            status_code=404,
            detail="La votaciÃ³n no existe."
        )

    return poll

@router.post(
    "/api/polls/{poll_id}/votes",
    response_model=VoteResponse,
    status_code=status.HTTP_201_CREATED,
)
async def cast_vote(
    poll_id: UUID,
    request: CastVoteRequest,
    x_voter_token: str = Header(
        ...,
        alias="X-Voter-Token",
        min_length=32,
        max_length=256,
    ),
    use_case: CastVote = Depends(get_cast_vote_use_case),
    results_use_case: GetPollResults = Depends(get_poll_results_use_case),
):
    voter_token_hash = hash_voter_token(x_voter_token)

    try:
        vote = use_case.execute(
            poll_id=poll_id,
            voter_token_hash=voter_token_hash,
            selected_option_ids=request.selected_option_ids,
        )
    except ValueError as error:
        message = str(error)

        if "no existe" in message:
            status_code = status.HTTP_404_NOT_FOUND
        elif (
            "ya ha votado" in message
            or "cerrada" in message
            or "fecha de cierre" in message
        ):
            status_code = status.HTTP_409_CONFLICT
        else:
            status_code = status.HTTP_422_UNPROCESSABLE_CONTENT

        raise HTTPException(
            status_code=status_code,
            detail=message,
        ) from error

    results = results_use_case.execute(poll_id)

    if results is not None:
        results_response = PollResultsResponse(
            poll_id=results.poll_id,
            poll_title=results.poll_title,
            total_votes=results.total_votes,
            results=[
                {
                    "option_id": result.option_id,
                    "option_text": result.option_text,
                    "votes": result.votes,
                    "points": result.points,
                    "percentage": result.percentage,
                }
                for result in results.results
            ],
        )

        await connection_manager.broadcast(
            poll_id,
            build_results_message(results_response),
        )

    return VoteResponse(
        id=vote.id,
        poll_id=vote.poll_id,
        selected_option_ids=vote.selected_option_ids,
        created_at=vote.created_at,
        updated_at=vote.updated_at,
    )

@router.put(
    "/api/polls/{poll_id}/votes",
    response_model=VoteResponse,
    status_code=status.HTTP_200_OK,
)
async def update_vote(
    poll_id: UUID,
    request: UpdateVoteRequest,
    x_voter_token: str = Header(
        ...,
        alias="X-Voter-Token",
        min_length=32,
        max_length=256,
    ),
    use_case: UpdateVote = Depends(get_update_vote_use_case),
    results_use_case: GetPollResults = Depends(get_poll_results_use_case),
):
    voter_token_hash = hash_voter_token(x_voter_token)

    try:
        vote = use_case.execute(
            poll_id=poll_id,
            voter_token_hash=voter_token_hash,
            selected_option_ids=request.selected_option_ids,
        )
    except ValueError as error:
        message = str(error)

        if "no existe" in message or "todavÃ­a no ha votado" in message:
            status_code = status.HTTP_404_NOT_FOUND
        elif (
            "cerrada" in message
            or "fecha de cierre" in message
        ):
            status_code = status.HTTP_409_CONFLICT
        else:
            status_code = status.HTTP_422_UNPROCESSABLE_CONTENT

        raise HTTPException(
            status_code=status_code,
            detail=message,
        ) from error

    results = results_use_case.execute(poll_id)

    if results is not None:
        results_response = PollResultsResponse(
            poll_id=results.poll_id,
            poll_title=results.poll_title,
            total_votes=results.total_votes,
            results=[
                {
                    "option_id": result.option_id,
                    "option_text": result.option_text,
                    "votes": result.votes,
                    "points": result.points,
                    "percentage": result.percentage,
                }
                for result in results.results
            ],
        )

        await connection_manager.broadcast(
            poll_id,
            build_results_message(results_response),
        )

    return VoteResponse(
        id=vote.id,
        poll_id=vote.poll_id,
        selected_option_ids=vote.selected_option_ids,
        created_at=vote.created_at,
        updated_at=vote.updated_at,
    )

@router.get(
    "/api/polls/{poll_id}/results",
    response_model=PollResultsResponse,
)
def get_poll_results(
    poll_id: UUID,
    use_case: GetPollResults = Depends(get_poll_results_use_case),
) -> PollResultsResponse:
    results = use_case.execute(poll_id)

    if results is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="La votaciÃ³n no existe.",
        )

    return PollResultsResponse(
        poll_id=results.poll_id,
        poll_title=results.poll_title,
        total_votes=results.total_votes,
        results=[
            {
                "option_id": result.option_id,
                "option_text": result.option_text,
                "votes": result.votes,
                "points": result.points,
                "percentage": result.percentage,
            }
            for result in results.results
        ],
    )

@router.websocket("/api/polls/{poll_id}/ws")
async def poll_updates(
    websocket: WebSocket,
    poll_id: UUID,
):
    await connection_manager.connect(poll_id, websocket)

    try:
        while True:
            await websocket.receive_text()

    except WebSocketDisconnect:
        connection_manager.disconnect(poll_id, websocket)
