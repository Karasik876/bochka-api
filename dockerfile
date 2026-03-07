
# Берем образ, в котором уже есть пакетный менеджер uv. 
# Приставка "AS builder" дает этому этапу имя, чтобы мы могли забрать отсюда файлы позже.
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS builder

# Указываем рабочую папку внутри контейнера, где будем всё собирать.
WORKDIR /app

# Настраиваем uv: просим компилировать файлы в байт-код для скорости...
ENV UV_COMPILE_BYTECODE=1
# ...и копировать файлы физически, а не создавать ярлыки (ссылки).
ENV UV_LINK_MODE=copy


# Мы временно "подключаем" файлы pyproject.toml и uv.lock, чтобы uv понял, что качать.
# --mount=type=cache сохраняет скачанные пакеты. Если ты поменяешь код в проекте, 
# Docker не будет заново качать половину интернета — он возьмет пакеты из кэша.
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --locked --no-install-project --no-dev



# Теперь, когда тяжелые библиотеки скачаны, копируем папку с кодом.
COPY src ./src

# Доустанавливаем сам твой проект  поверх скачанных библиотек.
# Флаг --no-dev говорит: "Не ставь библиотеки для тестов, мы готовимся к проду".
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev

# Выполняем требование задачи: берем чистый и легкий образ Python ИЗ ИНТЕРНЕТА.
# В нем НЕТ менеджера uv, нет кэшей, он весит минимум.
FROM python:3.12-slim AS runtime

# Снова задаем рабочую папку, уже в новом чистом контейнере.
WORKDIR /app

# === ГЛАВНАЯ МАГИЯ ДВУХЭТАПНОЙ СБОРКИ ===
# Копируем готовую папку с библиотеками (.venv) из этапа "builder" в наш чистовик.
COPY --from=builder /app/.venv /app/.venv

# Копируем папку с твоим кодом из этапа "builder" в чистовик.
COPY --from=builder /app/src ./src


# Жестко прописываем путь к нашей скопированной папке .venv в мозги Linux.
ENV PATH="/app/.venv/bin:$PATH"

# Отключаем создание лишних файлов кэша питона и буферизацию вывода 
# (чтобы логи сервера сразу сыпались в консоль Docker, а не зависали в памяти).
# мне непонятно пока похуй думаю
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

COPY alembic.ini ./
COPY ./alembic ./alembic


CMD  ["hypercorn", "src.main:app","--bind", "0.0.0.0:8000", "--reload"]
