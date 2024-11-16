from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
import aioboto3

POSTGRES_URL = os.environ.get("DATABASE_URL", "")
BUCKET_NAME = os.environ.get("BUCKET_NAME", "prompt-stack")

engine = create_engine(POSTGRES_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def init_db():
    # Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    # Initialize database session
    db = SessionLocal()
    try:
        from sandbox.default_packs import PACKS
        from db.models import Stack

        for pack in PACKS:
            existing_stack = db.query(Stack).filter(Stack.title == pack.title).first()
            if not existing_stack:
                stack = Stack(
                    title=pack.title,
                    description=pack.description,
                    from_registry=pack.from_registry,
                    sandbox_init_cmd=pack.sandbox_init_cmd,
                    sandbox_start_cmd=pack.sandbox_start_cmd,
                    prompt=pack.prompt,
                )
                db.add(stack)
        db.commit()
    finally:
        db.close()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_aws_client():
    client = aioboto3.Session()
    yield client
