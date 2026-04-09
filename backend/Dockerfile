FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Dependencias del sistema para compilar psycopg2 y similares
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
  && rm -rf /var/lib/apt/lists/*

# Instala dependencias de Python primero para aprovechar la caché
COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

# Copia el código de la aplicación
COPY app ./app

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD python -c "import sys, urllib.request; \
import os; \
url = f'http://localhost:8000/health'; \
req=urllib.request.Request(url); \
urllib.request.urlopen(req)" || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
