"""Prepare the internal connection, apply migrations, and start a single worker."""
import os
import sys

from alembic import command
from alembic.config import Config
from sqlalchemy.engine import URL


def main():
    """Build the URL without interpolating secrets and abort startup if Alembic fails."""
    os.environ['DATABASE_URL'] = URL.create(
        'postgresql+psycopg', username='votestupid',
        password=os.environ['POSTGRES_PASSWORD'], host='db',
        database='votestupid',
    ).render_as_string(hide_password=False)
    command.upgrade(Config('alembic.ini'), 'head')
    os.execv(sys.executable, [
        sys.executable, '-m', 'uvicorn', 'app.main:app',
        '--host', '0.0.0.0', '--port', '8000', '--workers', '1',
        '--proxy-headers', '--forwarded-allow-ips', os.environ['NGINX_INTERNAL_IP'],
        '--ws-max-size', '1024',
    ])


if __name__ == '__main__':
    main()
