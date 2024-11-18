import os
import secrets


def _bool_env(key, default: bool = False):
    val = os.getenv(key, str(default)).lower()
    return val == "true" or val == "1"


# Database configuration
DATABASE_URL = os.environ.get("DATABASE_URL", "")

# AWS configuration
AWS_ACCESS_KEY_ID = os.environ.get("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.environ.get("AWS_SECRET_ACCESS_KEY")
AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")
BUCKET_NAME = os.environ.get("BUCKET_NAME", "prompt-stack")

# JWT configuration
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", secrets.token_urlsafe(32))

# OpenAI configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_FAST_MODEL = os.getenv("OPENAI_FAST_MODEL", "gpt-4o-mini")
OPENAI_MAIN_MODEL = os.getenv("OPENAI_MAIN_MODEL", "gpt-4o")

RUN_PERIODIC_CLEANUP = _bool_env("RUN_PERIODIC_CLEANUP", default=True)
