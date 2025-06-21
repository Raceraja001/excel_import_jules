import asyncio
from logging.config import fileConfig
import os
import sys

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context

# This will add the 'app' directory to the sys.path
# allowing Alembic to find your models and config.
sys.path.append(os.path.join(sys.path[0], 'app'))

# Import your app's settings and Base model
# This is how Alembic will get the DB URL and know about your models.
from config import settings  # Your Pydantic settings from app.config
from models import Base     # Your SQLAlchemy Base from app.models or app.database

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Set the sqlalchemy.url from your application settings
# This overrides the sqlalchemy.url in alembic.ini if DATABASE_URL is set in your environment
# and loaded by your Pydantic settings.
db_url = settings.DATABASE_URL
if not db_url:
    raise ValueError("DATABASE_URL is not set in the environment or app config.")
config.set_main_option("sqlalchemy.url", db_url)


# add your model's MetaData object here
# for 'autogenerate' support
# from myapp import mymodel
# target_metadata = mymodel.Base.metadata
target_metadata = Base.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        # compare_type=True, # Enable type comparison
        # compare_server_default=True # Enable server default comparison
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    """
    Run actual migrations.
    """
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        # compare_type=True, # Enable type comparison
        # compare_server_default=True # Enable server default comparison
        # Include other options like `render_as_batch` if needed for SQLite
        # render_as_batch=True
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool, # Use NullPool for async, same as in your app
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
