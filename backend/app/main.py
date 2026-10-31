from fastapi import FastAPI

app = FastAPI(
    title="VoteStupid",
    description="Una aplicacion para crear votaciones y compartirlas con amigos."
)

@app.get("/")
def home():
    return {
        "message": "¡Bienvenido a VoteStupid!"
    }

@app.get("/api/info")
def get_info():
    return {
        "app": "VoteStupid",
        "version": "0.1.0",
        "status": "En desarrollo",
        "description": "Aplicación de votaciones para amigos"
    }

@app.get("/api/status")
def get_status():
    return {
    "online": True,
    "message": "VoteStupid está funcionando"
    }