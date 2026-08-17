FROM python:3.13-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-cache

COPY . .

# El build no depende de un archivo .env.build. Los valores seguros por
# defecto y RepositoryEmpty permiten recolectar los estáticos.
RUN DJANGO_ENV=build DJANGO_SETTINGS_MODULE=core.settings.development \
    uv run python manage.py collectstatic --noinput

EXPOSE 8000

CMD ["uv", "run", "gunicorn", "core.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3"]
