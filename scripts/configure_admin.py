"""Generate the administrator password hash without displaying or storing the original password."""
from getpass import getpass
from pathlib import Path
import argparse
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
from app.infrastructure.security.admin_session import password_hash


def main():
    """Request and confirm a sufficiently long password, exposing only its hash."""
    parser = argparse.ArgumentParser(description="Configure the administrator password without displaying it.")
    parser.add_argument('--write-env', action='store_true', help='Store the hash in the private project .env file.')
    parser.add_argument('--local-http', action='store_true', help='Allow cookies without Secure only for local HTTP development.')
    args = parser.parse_args()
    password = getpass("Nueva contraseña de administración (entre 16 y 256 caracteres): ")
    confirmation = getpass("Repite la contraseña: ")
    if not 16 <= len(password) <= 256 or password != confirmation:
        raise SystemExit("Las contraseñas deben coincidir y tener entre 16 y 256 caracteres.")
    encoded = password_hash(password)
    if args.write_env:
        from dotenv import set_key
        env_path = Path(__file__).resolve().parents[1] / '.env'
        set_key(str(env_path), 'ADMIN_PASSWORD_HASH', encoded)
        set_key(str(env_path), 'ADMIN_COOKIE_SECURE', 'false' if args.local_http else 'true')
        print('Configuración guardada. Reinicia el backend para utilizar la nueva contraseña.')
    else:
        print("ADMIN_PASSWORD_HASH=" + encoded)


if __name__ == "__main__":
    main()
