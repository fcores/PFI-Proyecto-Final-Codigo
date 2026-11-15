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
COPY docker-entrypoint.sh .

EXPOSE 8000

# http o https segun como haya arrancado uvicorn (ver docker-entrypoint.sh)
HEALTHCHECK --interval=30s --timeout=10s --retries=3 --start-period=60s \
    CMD python -m backend.healthcheck

# Bootstrap de la base y uvicorn, con TLS si la task definition inyecta el
# certificado. Detalle en docker-entrypoint.sh.
CMD ["sh", "/app/docker-entrypoint.sh"]
