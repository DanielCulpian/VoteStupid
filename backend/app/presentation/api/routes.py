from app.domain.vote_rule_error import VoteRuleError
from typing import Literal
from fastapi import Query
from app.infrastructure.security.admin_session import require_admin_session
from app.presentation.api.schemas import PollPage, PollSummary
from app.domain.entities.poll_type import PollType
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
from app.presentation.api.schemas import (
    CreatePollRequest,
    PollResponse,
    PollCreatedResponse,
    CastVoteRequest,
    VoteResponse,
    UpdateVoteRequest,
)
from app.application.use_cases.cast_vote import CastVote
from app.infrastructure.security.voter_token import hash_voter_token
from app.application.use_cases.update_vote import UpdateVote
from app.application.use_cases.get_poll_results import GetPollResults
from app.presentation.api.schemas import PollResultsResponse
from uuid import UUID

from app.application.use_cases.get_poll import GetPoll
from app.application.use_cases.close_poll import ClosePoll
from app.application.use_cases.reopen_poll import ReopenPoll

from app.presentation.api.dependencies import (
    get_admin_poll as get_admin_poll_dependency,
    get_close_poll_use_case,
    get_reopen_poll_use_case,
)

router = APIRouter()

def build_results_message(results: PollResultsResponse) -> dict:
    """Serialize results into a WebSocket update message."""
    return {
        "type": "results_updated",
        "results": results.model_dump(mode="json"),
    }

def build_poll_status_message(poll: Poll) -> dict:
    """Build the WebSocket message containing the poll state."""
    return {
        "type": "poll_status_updated",
        "is_active": poll.is_active,
    }

@router.get("/")
def home():
    """Return the API welcome message."""
    return {
        "message": "¡Bienvenido a VoteStupid!"
    }


@router.get("/api/info")
def get_info():
    """Return the application name, version, and description."""
    return {
        "app": "VoteStupid",
        "version": "0.1.0",
        "status": "En desarrollo",
        "description": "Aplicación de votaciones para amigos"
    }


@router.get("/api/status")
def get_status():
    """Indicate that the API is available."""
    return {
        "online": True,
        "message": "VoteStupid está funcionando"
    }

@router.post(
    "/api/polls",
    response_model=PollCreatedResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_admin_session)],
)
async def create_poll(
    request: CreatePollRequest,
    poll_repository: PollRepository = Depends(get_poll_repository)
) -> PollCreatedResponse:
    """Create a poll and return its data and administration token."""
    use_case = CreatePoll(poll_repository)

    result = use_case.execute(
        title=request.title,
        option_texts=request.option_texts,
        poll_type=request.poll_type,
        description=request.description,
        max_selections=request.max_selections,
        closes_at=request.closes_at
    )

    poll = result.poll

    await connection_manager.broadcast(UUID(int=0), build_poll_status_message(poll))

    return PollCreatedResponse(
        id=poll.id,
        title=poll.title,
        description=poll.description,
        poll_type=poll.poll_type,
        options=poll.options,
        max_selections=poll.max_selections,
        closes_at=poll.closes_at,
        is_active=poll.is_active,
        created_at=poll.created_at,
        admin_token=result.admin_token,
    )

@router.get("/api/polls", response_model=PollPage)
def list_public_polls(
    state: Literal["all", "active", "inactive"] = "all",
    poll_type: PollType | None = None,
    offset: int = Query(0, ge=0, le=1000000),
    limit: int = Query(24, ge=1, le=100),
    repository: PollRepository = Depends(get_poll_repository),
):
    """Expose only public metadata and apply combined filters with stable pagination."""
    polls, total = repository.list_polls(state, poll_type.value if poll_type else None, offset, limit)
    return PollPage(items=[PollSummary.model_validate(poll) for poll in polls], total=total, offset=offset, limit=limit)


@router.get("/api/admin/polls", response_model=PollPage, dependencies=[Depends(require_admin_session)])
def list_admin_polls(
    state: Literal["all", "active", "inactive"] = "all", poll_type: PollType | None = None,
    offset: int = Query(0, ge=0, le=1000000), limit: int = Query(24, ge=1, le=100),
    repository: PollRepository = Depends(get_poll_repository),
):
    """Let the administrator recover all polls without their secret links."""
    return list_public_polls(state, poll_type, offset, limit, repository)


@router.get(
    "/api/polls/{poll_id}",
    response_model=PollResponse
)
def get_poll(
    poll_id: UUID,
    poll_repository: PollRepository = Depends(get_poll_repository)
) -> Poll:
    """Return the requested poll or an error if it does not exist."""
    use_case = GetPoll(poll_repository)

    poll = use_case.execute(poll_id)

    if poll is None:
        raise HTTPException(
            status_code=404,
            detail="La votación no existe."
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
        pattern=r"^[A-Za-z0-9_-]+$",
    ),
    use_case: CastVote = Depends(get_cast_vote_use_case),
    results_use_case: GetPollResults = Depends(get_poll_results_use_case),
):
    """Register a vote and broadcast updated results over WebSocket."""
    voter_token_hash = hash_voter_token(x_voter_token)

    try:
        vote = use_case.execute(
            poll_id=poll_id,
            voter_token_hash=voter_token_hash,
            selected_option_ids=request.selected_option_ids,
        )
    except VoteRuleError as error:
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
        pattern=r"^[A-Za-z0-9_-]+$",
    ),
    use_case: UpdateVote = Depends(get_update_vote_use_case),
    results_use_case: GetPollResults = Depends(get_poll_results_use_case),
):
    """Update an existing vote and broadcast the new results over WebSocket."""
    voter_token_hash = hash_voter_token(x_voter_token)

    try:
        vote = use_case.execute(
            poll_id=poll_id,
            voter_token_hash=voter_token_hash,
            selected_option_ids=request.selected_option_ids,
        )
    except VoteRuleError as error:
        message = str(error)

        if "no existe" in message or "todavía no ha votado" in message:
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
    """Return the poll results or an error if the poll does not exist."""
    results = use_case.execute(poll_id)

    if results is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="La votación no existe.",
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

@router.websocket("/api/polls/catalog/ws")
async def catalog_updates(websocket: WebSocket):
    """Notify public catalog changes through a single subscription per visitor."""
    await connection_manager.connect(UUID(int=0), websocket)
    try:
        while True:
            message = await websocket.receive()
            if message["type"] == "websocket.disconnect":
                break
            await websocket.close(code=1008)
            break
    finally:
        connection_manager.disconnect(UUID(int=0), websocket)


@router.websocket("/api/polls/{poll_id}/ws")
async def poll_updates(
    websocket: WebSocket,
    poll_id: UUID,
):
    """Maintain the WebSocket connection and remove it when the client disconnects."""
    await connection_manager.connect(poll_id, websocket)

    try:
        while True:
            message = await websocket.receive()
            if message["type"] == "websocket.disconnect":
                break
            # This channel only publishes events; client write messages are not accepted.
            await websocket.close(code=1008)
            break

    except WebSocketDisconnect:
        pass
    finally:
        connection_manager.disconnect(poll_id, websocket)

@router.put("/api/admin/polls/{poll_id}/close", response_model=PollResponse)
async def close_poll(
    poll_id: UUID,
    admin_poll: Poll = Depends(get_admin_poll_dependency),
    use_case: ClosePoll = Depends(get_close_poll_use_case),
):
    """Close an authorized poll and broadcast its state over WebSocket."""
    poll = use_case.execute(admin_poll.id)

    await connection_manager.broadcast(
        poll.id,
        build_poll_status_message(poll),
    )
    await connection_manager.broadcast(UUID(int=0), build_poll_status_message(poll))

    return PollResponse(
        id=poll.id,
        title=poll.title,
        description=poll.description,
        poll_type=poll.poll_type,
        options=poll.options,
        max_selections=poll.max_selections,
        closes_at=poll.closes_at,
        is_active=poll.is_active,
        created_at=poll.created_at,
    )


@router.put("/api/admin/polls/{poll_id}/reopen", response_model=PollResponse)
async def reopen_poll(
    poll_id: UUID,
    admin_poll: Poll = Depends(get_admin_poll_dependency),
    use_case: ReopenPoll = Depends(get_reopen_poll_use_case),
):
    """Reopen an authorized poll and broadcast its state over WebSocket."""
    poll = use_case.execute(admin_poll.id)

    await connection_manager.broadcast(
        poll.id,
        build_poll_status_message(poll),
    )
    await connection_manager.broadcast(UUID(int=0), build_poll_status_message(poll))

    return PollResponse(
        id=poll.id,
        title=poll.title,
        description=poll.description,
        poll_type=poll.poll_type,
        options=poll.options,
        max_selections=poll.max_selections,
        closes_at=poll.closes_at,
        is_active=poll.is_active,
        created_at=poll.created_at,
    )

@router.get(
    "/api/admin/polls/{poll_id}",
    response_model=PollResponse,
)
def get_admin_poll_details(
    admin_poll: Poll = Depends(get_admin_poll_dependency),
) -> PollResponse:
    """Return poll data after validating administrative access."""
    return PollResponse(
        id=admin_poll.id,
        title=admin_poll.title,
        description=admin_poll.description,
        poll_type=admin_poll.poll_type,
        options=admin_poll.options,
        max_selections=admin_poll.max_selections,
        closes_at=admin_poll.closes_at,
        is_active=admin_poll.is_active,
        created_at=admin_poll.created_at,
    )
