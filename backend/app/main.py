
import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.infrastructure.security.api_protection import ApiProtection, RateLimiter, SafeAccessLog, allowed_origins
from app.presentation.api.routes import router
from app.presentation.api.auth_routes import router as auth_router


async def validation_error(request: Request, error: RequestValidationError):
    """Devuelve errores de validación sin repetir valores, tokens ni contexto interno."""
    fields = {"body", "path", "query", "header", "poll_id", "title", "description",
              "option_texts", "poll_type", "max_selections", "closes_at",
              "selected_option_ids", "X-Admin-Token", "X-Voter-Token"}
    details = []
    for item in error.errors():
        location = [part for part in item["loc"] if part in fields or isinstance(part, int)]
        details.append({"loc": location, "msg": "Dato no válido.", "type": item["type"]})
    return JSONResponse({"detail": details}, status_code=422)


def create_app() -> FastAPI:
    """Construye una API con protecciones activas y estado aislado por instancia."""
    application = FastAPI(title="VoteStupid", description="Votaciones anónimas para amigos.")
    origins = allowed_origins()
    limiter = RateLimiter()
    application.state.rate_limiter = limiter
    application.add_exception_handler(RequestValidationError, validation_error)
    application.add_middleware(ApiProtection, limiter=limiter, origins=origins)
    application.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE"],
        allow_headers=["Content-Type", "X-Admin-Token", "X-Voter-Token", "X-Requested-With"],
        expose_headers=["Retry-After"],
    )
    for name in ["uvicorn.access", "uvicorn.error"]:
        logger = logging.getLogger(name)
        if not any(isinstance(filter_, SafeAccessLog) for filter_ in logger.filters):
            logger.addFilter(SafeAccessLog())
    application.include_router(auth_router)
    application.include_router(router)
    return application


app = create_app()
