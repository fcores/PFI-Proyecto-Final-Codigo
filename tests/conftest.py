"""Configuracion de pytest y fixtures compartidas."""

import os

os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("ENCRYPTION_KEY_DEV", "dGVzdGtleXRlc3RrZXl0ZXN0a2V5dGVzdGtleT0=")
