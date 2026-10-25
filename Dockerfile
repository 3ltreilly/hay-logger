# For more information, please refer to https://aka.ms/vscode-docker-python
FROM python:3.11-slim

EXPOSE 8000

# Keeps Python from generating .pyc files in the container
ENV PYTHONDONTWRITEBYTECODE=1

# Turns off buffering for easier container logging
ENV PYTHONUNBUFFERED=1

# uv from its official image, pinned so builds are repeatable
COPY --from=ghcr.io/astral-sh/uv:0.11.2 /uv /bin/uv
# use this image's Python instead of downloading one, and copy packages into the venv
# rather than linking them to uv's cache
ENV UV_PYTHON_DOWNLOADS=never
ENV UV_LINK_MODE=copy

WORKDIR /app

# install dependencies before copying the code, so this layer is reused until uv.lock changes
COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-dev
# uv installs into /app/.venv; put it first on PATH so `python` below is the venv's
ENV PATH="/app/.venv/bin:$PATH"

COPY hay_logger ./hay_logger
COPY log_app ./log_app
COPY manage.py ./
COPY readme.md ./

# get the database, for debugging
# COPY db.sqlite3 ./

# Creates a non-root user with an explicit UID and adds permission to access the /app folder
# For more info, please refer to https://aka.ms/vscode-docker-python-configure-containers
# RUN adduser -u 5678 --disabled-password --gecos "" appuser && chown -R appuser /app
# USER appuser

# During debugging, this entry point will be overridden. For more information, please refer to https://aka.ms/vscode-docker-python-debug
# CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--log-level", "debug", "hay_logger.wsgi"]
# go to this website
# 127.0.0.1:8000/

CMD ["sh", "-c", "python manage.py migrate --noinput && python manage.py runserver 0.0.0.0:8000"]
