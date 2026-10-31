from fastapi import FastAPI
from app.presentation.api.routes import router

app = FastAPI(
    title="VoteStupid",
    description="Una aplicacion para crear votaciones y compartirlas con amigos."
)

app.include_router(router)