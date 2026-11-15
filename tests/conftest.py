"""Configuracion de pytest y fixtures compartidas."""

import os

os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("ENCRYPTION_KEY_DEV", "dGVzdGtleXRlc3RrZXl0ZXN0a2V5dGVzdGtleT0=")
# Los tests corren en memoria: una variable de entorno (aunque este vacia) le
# gana al .env local, que puede tener el DATABASE_URL de un entorno real.
# Los tests que necesitan Postgres usan TEST_DATABASE_URL explicitamente.
os.environ.setdefault("DATABASE_URL", "")
os.environ.setdefault("FABRIC_GATEWAY_URL", "")
