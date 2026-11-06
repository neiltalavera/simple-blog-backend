import os

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings

engine_options = {"pool_pre_ping": True}
if os.environ.get("AWS_LAMBDA_FUNCTION_NAME"):
    # Keep each warm Lambda environment's connection footprint small.
    engine_options.update(pool_size=1, max_overflow=0, pool_recycle=300)

engine = create_engine(settings.runtime_database_url, **engine_options)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
