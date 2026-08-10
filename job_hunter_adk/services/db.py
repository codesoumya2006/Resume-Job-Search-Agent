import os
from datetime import datetime, timezone
from sqlalchemy import create_engine, Column, Integer, String, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker
from schemas.job_listing import JobListing

DB_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data')
os.makedirs(DB_DIR, exist_ok=True)
DB_PATH = os.path.join(DB_DIR, 'applications.db')

engine = create_engine(f'sqlite:///{DB_PATH}', echo=False)
Base = declarative_base()
SessionLocal = sessionmaker(bind=engine)

class Application(Base):
    __tablename__ = 'applications'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    job_id = Column(String, index=True)
    company = Column(String)
    title = Column(String)
    status = Column(String, default="applied")
    applied_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    notes = Column(String, nullable=True)

Base.metadata.create_all(engine)

def record_application(job_listing: JobListing, status: str) -> None:
    """Record a job application in the SQLite database."""
    session = SessionLocal()
    try:
        app = Application(
            job_id=str(job_listing.id),
            company=job_listing.company,
            title=job_listing.title,
            status=status
        )
        session.add(app)
        session.commit()
    finally:
        session.close()
