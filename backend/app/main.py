
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.presentation.api.routes import router

app = FastAPI(
    title="VoteStupid",
    description="Una aplicacion para crear votaciones y compartirlas con amigos."
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:5174",
    ],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)
