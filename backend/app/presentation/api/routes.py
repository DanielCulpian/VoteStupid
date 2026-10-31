from fastapi import APIRouter

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