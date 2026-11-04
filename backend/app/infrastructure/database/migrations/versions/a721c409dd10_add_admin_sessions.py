"""Añade sesiones administrativas revocables sin guardar sus secretos originales."""
from alembic import op
import sqlalchemy as sa

revision = "a721c409dd10"
down_revision = "6a08f353e13c"
branch_labels = None
depends_on = None


def upgrade():
    """Crea la tabla de sesiones y el índice de caducidad."""
    op.create_table("admin_sessions", sa.Column("token_hash", sa.String(64), primary_key=True),
                    sa.Column("credential_version", sa.String(64), nullable=False),
                    sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False))
    op.create_index("ix_admin_sessions_expires_at", "admin_sessions", ["expires_at"])


def downgrade():
    """Retira exclusivamente las sesiones administrativas."""
    op.drop_index("ix_admin_sessions_expires_at", table_name="admin_sessions")
    op.drop_table("admin_sessions")
