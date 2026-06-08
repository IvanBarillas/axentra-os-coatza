FROM python:3.12-slim
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
WORKDIR /app

# Sincronización ultrarrápida usando tu uv.lock y pyproject.toml existentes
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-cache

COPY . .

# Recolectar archivos estáticos de Django de manera silenciosa al compilar
RUN uv run python manage.py collectstatic --noinput

# 🚨 Puerto homologado para Nginx Proxy Manager
EXPOSE 8000

# Comando por defecto (Sobrescribible en modo desarrollo por el compose)
CMD ["uv", "run", "gunicorn", "core.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3"]