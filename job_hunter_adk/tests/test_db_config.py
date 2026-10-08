import os
from unittest.mock import patch
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from schemas.job_listing import JobListing
from services.db import (
    get_database_url,
    get_engine,
    record_application,
    Base,
    Application
)


def test_default_database_behavior() -> None:
    """
    When DATABASE_URL is not set, defaults to local SQLite applications.db.
    """
    with patch.dict(os.environ, {}, clear=True):
        # Ensure DATABASE_URL is absent
        os.environ.pop("DATABASE_URL", None)
        url = get_database_url()
        assert url.startswith("sqlite:///")
        assert "applications.db" in url
        
        engine = get_engine()
        assert "sqlite" in engine.name


def test_configured_database_url_sqlite_custom() -> None:
    """
    When DATABASE_URL is set, uses the configured database URL.
    """
    custom_url = "sqlite:///:memory:"
    with patch.dict(os.environ, {"DATABASE_URL": custom_url}):
        url = get_database_url()
        assert url == custom_url
        
        engine = get_engine()
        import urllib.parse
        assert urllib.parse.unquote(str(engine.url)) == custom_url


def test_configured_database_url_normalizes_postgres_prefix() -> None:
    """
    When DATABASE_URL starts with 'postgres://', normalizes to 'postgresql://' for SQLAlchemy.
    """
    heroku_style_url = "postgres://dbuser:secret@localhost:5432/production_db"
    with patch.dict(os.environ, {"DATABASE_URL": heroku_style_url}):
        url = get_database_url()
        assert url.startswith("postgresql://")
        assert "dbuser:secret@localhost:5432/production_db" in url


def test_record_application_with_configured_database() -> None:
    """
    Demonstrates recording an application into a dedicated configured database instance.
    """
    from sqlalchemy.pool import StaticPool
    custom_engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=False
    )
    Base.metadata.create_all(custom_engine)
    CustomSessionLocal = sessionmaker(bind=custom_engine)

    import uuid
    from schemas.job_listing import compute_job_hash

    job_id = str(uuid.uuid4())
    job = JobListing(
        id=job_id,
        title="Site Reliability Engineer",
        company="Reliability Co",
        location="Remote",
        work_mode="remote",
        job_type="permanent",
        source="linkedin",
        url="https://linkedin.com/jobs/view/999",
        description="Reliability and observability infrastructure.",
        stipend_or_salary="Competitive",
        posted_date="2026-03-01",
        raw_text_hash=compute_job_hash("Site Reliability Engineer", "Reliability Co", "Reliability and observability infrastructure.")
    )

    record_application(job, "submitted", session_factory=CustomSessionLocal)

    with CustomSessionLocal() as session:
        records = session.query(Application).filter_by(job_id=job_id).all()
        assert len(records) == 1
        assert records[0].title == "Site Reliability Engineer"
        assert records[0].status == "submitted"
