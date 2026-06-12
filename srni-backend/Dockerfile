# ============================================================
# SRNI Backend — Imagen de producción (Django + Gunicorn)
# Python 3.12 (todas las dependencias tienen wheels estables)
# ============================================================
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Dependencias de sistema mínimas (libpq para psycopg, curl para healthcheck)
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        libpq-dev \
        curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# El módulo de settings se inyecta por variable de entorno (DJANGO_SETTINGS_MODULE).
# Por defecto wsgi.py usa srni.settings.production; en este servidor se usa
# srni.settings.servidor (acceso por IP/HTTP en fase de pruebas).
EXPOSE 8001

CMD ["gunicorn", "srni.wsgi:application", "--bind", "0.0.0.0:8001", "--workers", "4", "--timeout", "120"]
