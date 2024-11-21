import os
import secrets
from typing import List


def _bool_env(key, default: bool = False):
    val = os.getenv(key, str(default)).lower()
    return val == "true" or val == "1"


def _int_env(key, default: int = 0):
    return int(os.getenv(key, str(default)))


def _enum_env(key, options: List[str], default: str) -> str:
    val = os.getenv(key, default).strip().lower()
    normalized_options = [opt.strip().lower() for opt in options]
    if val not in normalized_options:
        raise ValueError(f"{key} must be one of {options}")
    return val


# Database configuration
DATABASE_URL = os.environ.get("DATABASE_URL", "")

# AWS configuration
AWS_ACCESS_KEY_ID = os.environ.get("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.environ.get("AWS_SECRET_ACCESS_KEY")
AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")
BUCKET_NAME = os.environ.get("BUCKET_NAME", "prompt-stack")

# Secrets configuration
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", secrets.token_urlsafe(32))
UNSPLASH_ACCESS_KEY = os.getenv("UNSPLASH_ACCESS_KEY")

# AI configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
FAST_PROVIDER = _enum_env("FAST_PROVIDER", ["openai", "anthropic"], default="openai")
MAIN_PROVIDER = _enum_env("MAIN_PROVIDER", ["openai", "anthropic"], default="anthropic")
FAST_MODEL = os.getenv("FAST_MODEL", "gpt-4o-mini")
MAIN_MODEL = os.getenv("MAIN_MODEL", "claude-3-5-sonnet-20241022")

# Misc configuration
RUN_PERIODIC_CLEANUP = _bool_env("RUN_PERIODIC_CLEANUP", default=True)
TARGET_PREPARED_SANDBOXES_PER_STACK = _int_env("TARGET_PREPARED_SANDBOXES_PER_STACK", 3)

# User config
CREDITS_DEFAULT = _int_env("CREDITS_DEFAULT", 30)
CREDITS_CHAT_COST = _int_env("CREDITS_CHAT_COST", 10)
