FROM python:3.12-slim

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends libgomp1 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY sql/ sql/
COPY backend/ backend/
COPY ml_models/artefactos/ ml_models/artefactos/
COPY alembic.ini .
COPY alembic/ alembic/

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --retries=3 --start-period=60s \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/')"

# El bootstrap aplica sql/schema.sql y luego 'alembic upgrade head'. Si falla,
# el contenedor sale != 0 a proposito: preferimos un crash loop visible antes
# que una app sirviendo trafico contra un esquema roto.
CMD ["sh", "-c", "python -m backend.db_bootstrap && exec uvicorn backend.main:app --host 0.0.0.0 --port 8000"]
