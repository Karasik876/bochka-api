from logging.config import fileConfig
from pathlib import Path

from sqlalchemy import engine_from_config, pool, inspect, Integer, Column, String, TIMESTAMP, text

from alembic import context  # type: ignore
from src.config import get_settings
from src.models import Base

import os
import yaml
from alembic import context
from sqlalchemy import MetaData, Table
from sqlalchemy.orm import sessionmaker

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config
settings = get_settings()

section = config.config_ini_section
config.set_section_option(section, "DATABASE_URL", str(settings.DATABASE_URL))

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
# from myapp import mymodel
# target_metadata = mymodel.Base.metadata
target_metadata = Base.metadata


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


def ensure_seed_history_table_exists(connection):
    """
    Создает таблицу seed_history, если она не существует.
    """
    metadata = MetaData()

    # Определяем структуру таблицы seed_history
    seed_history_table = Table(
        'seed_history',
        metadata,
        Column('id', Integer, primary_key=True, autoincrement=True),  # Служебное поле с автоинкрементом
        Column('seed_id', String(255), nullable=False, unique=True),  # Уникальный идентификатор сида
        Column('table_name', String(255), nullable=False),
        Column('applied_at', TIMESTAMP, server_default=text('CURRENT_TIMESTAMP'))
    )

    # Проверяем, существует ли таблица
    inspector = inspect(connection)
    if 'seed_history' not in inspector.get_table_names():
        # Создаем таблицу
        metadata.create_all(bind=connection)
        print("Таблица seed_history создана.")


def run_seeds_after_migrate(connection):
    """
    Применяет сиды из файла seeds.yml, пропуская уже примененные записи.
    """
    ensure_seed_history_table_exists(connection)

    # Создаем сессию
    Session = sessionmaker(bind=connection)
    session = Session()

    seeds_file_path = os.path.join(Path(__file__).resolve().parent, 'seeds.yml')
    if not os.path.exists(seeds_file_path):
        print(f"Файл seeds.yml не найден: {seeds_file_path}")
        return

    with open(seeds_file_path, 'r') as f:
        seeds_data = yaml.safe_load(f)

    if not seeds_data:
        print("Файл seeds.yml пуст.")
        return

    metadata = MetaData()
    metadata.reflect(bind=connection)

    # Применяем сиды в порядке их следования в файле
    for table_name, rows in seeds_data.items():
        if table_name not in metadata.tables:
            print(f"Таблица {table_name} не найдена в базе данных.")
            continue

        table = metadata.tables[table_name]
        # Получаем список уже примененных seed_id для этой таблицы
        applied_seeds = {
            row.seed_id for row in session.execute(
                text("SELECT seed_id FROM seed_history WHERE table_name = :table_name"),
                {'table_name': table_name}
            )
        }

        # Фильтруем записи, оставляем только те, которые еще не были применены
        new_rows = []
        for row in rows:
            seed_id = row.get('seed_id')  # Уникальный идентификатор сида
            if not seed_id:
                print(f"Запись в таблице {table_name} не содержит 'seed_id'. Пропускаем.")
                continue
            if seed_id in applied_seeds:
                continue
            new_rows.append(row)

        if not new_rows:
            continue

        # Вставляем новые записи
        session.execute(table.insert(), new_rows)

        # Фиксируем применение данных для каждой записи
        for row in new_rows:
            seed_id = row.get('seed_id')
            session.execute(
                text("INSERT INTO seed_history (seed_id, table_name) VALUES (:seed_id, :table_name)"),
                {'seed_id': seed_id, 'table_name': table_name}
            )

        print(f"Данные для таблицы {table_name} применены. Добавлено {len(new_rows)} записей.")

    session.commit()


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

            # Применяем сиды только при наличии x-аргумента run_seeds
            x_args = context.get_x_argument(as_dictionary=True)
            if x_args.get('run_seeds', 'false').lower() == 'true':
                run_seeds_after_migrate(connection)


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
