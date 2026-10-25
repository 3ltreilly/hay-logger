# For more information, please refer to https://aka.ms/vscode-docker-python
FROM python:3.11-slim

EXPOSE 8000

# Keeps Python from generating .pyc files in the container
ENV PYTHONDONTWRITEBYTECODE=1

# Turns off buffering for easier container logging
ENV PYTHONUNBUFFERED=1

# production: debug off. DJANGO_SECRET_KEY comes from the env file on the server
ENV DJANGO_DEBUG=0

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

# copy static files (the admin's CSS) into STATIC_ROOT for WhiteNoise to serve. Settings
# refuse to load without a real key when debug is off, and this step needs none, so
# give it a throwaway one
RUN DJANGO_SECRET_KEY=collectstatic-only python manage.py collectstatic --noinput

# get the database, for debugging
# COPY db.sqlite3 ./

# Creates a non-root user with an explicit UID and adds permission to access the /app folder
# For more info, please refer to https://aka.ms/vscode-docker-python-configure-containers
# RUN adduser -u 5678 --disabled-password --gecos "" appuser && chown -R appuser /app
# USER appuser

# apply any new migrations, then serve the app with gunicorn (runserver is for development)
CMD ["sh", "-c", "python manage.py migrate --noinput && gunicorn --bind 0.0.0.0:8000 --workers 2 hay_logger.wsgi"]
