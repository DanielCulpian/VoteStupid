"""Genera el hash de la contraseña administrativa sin mostrar ni guardar el texto original."""
from getpass import getpass
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
from app.infrastructure.security.admin_session import password_hash


def main():
    """Solicita y confirma una contraseña suficientemente larga y muestra solo su hash."""
    password = getpass("Nueva contraseña de administración (mínimo 16 caracteres): ")
    confirmation = getpass("Repite la contraseña: ")
    if not 16 <= len(password) <= 256 or password != confirmation:
        raise SystemExit("Las contraseñas deben coincidir y tener al menos 16 caracteres.")
    print("ADMIN_PASSWORD_HASH=" + password_hash(password))


if __name__ == "__main__":
    main()
