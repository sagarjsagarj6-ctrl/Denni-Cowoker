"""Minimal Alembic entry point; the reference application uses idempotent SQL migrations."""

from alembic import context


def run_migrations_online() -> None:
    context.configure(url=context.config.get_main_option("sqlalchemy.url"), literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()


run_migrations_online()
