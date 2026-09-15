from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# URL은 alembic.ini가 아니라 전역 Secret 매니저(.env)에서 가져온다
from core.matrix.grid_keymaker_secret_manager import get_settings
from core.matrix.grid_oracle_database_manager import OrmBase

# autogenerate 대상 — 모든 BC의 ORM 모듈을 여기 등록한다 (import만 하면 metadata에 잡힌다)
import apps.convenience.adapter.outbound.orms.convenience_store_orm  # noqa: F401
import apps.funding.adapter.outbound.orms.funding_program_orm  # noqa: F401
import apps.master.adapter.outbound.orms.district_orm  # noqa: F401
import apps.master.adapter.outbound.orms.region_orm  # noqa: F401
import apps.master.adapter.outbound.orms.industry_orm  # noqa: F401
import apps.master.adapter.outbound.orms.industry_source_code_orm  # noqa: F401
import apps.master.adapter.outbound.orms.industry_subcategory_orm  # noqa: F401
import apps.master.adapter.outbound.orms.population_stat_orm  # noqa: F401
import apps.metric.adapter.outbound.orms.region_industry_metric_orm  # noqa: F401
import apps.news.adapter.outbound.orms.news_article_orm  # noqa: F401
import apps.rag.adapter.outbound.orms.rag_chunk_orm  # noqa: F401
import apps.rent.adapter.outbound.orms.rent_price_orm  # noqa: F401
import apps.shock.adapter.outbound.orms.interest_rate_orm  # noqa: F401
import apps.shock.adapter.outbound.orms.shock_event_industry_orm  # noqa: F401
import apps.shock.adapter.outbound.orms.shock_event_orm  # noqa: F401
import apps.shock.adapter.outbound.orms.shock_event_region_orm  # noqa: F401
import apps.store.adapter.outbound.orms.academy_course_orm  # noqa: F401
import apps.store.adapter.outbound.orms.store_orm  # noqa: F401
import apps.tobacco.adapter.outbound.orms.tobacco_retailer_orm  # noqa: F401

config.set_main_option("sqlalchemy.url", get_settings().database_url)
target_metadata = OrmBase.metadata

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
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
