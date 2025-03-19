from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
import os
from datetime import datetime
import logging

# Configure logging
logger = logging.getLogger(__name__)

# Get database URL from environment variable or use an SQLite database
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./transcripts.db")

# Create database engine
# For SQLite (file-based database):
if DATABASE_URL.startswith("sqlite"):
    engine = create_engine(
        DATABASE_URL, 
        connect_args={"check_same_thread": False},
        poolclass=StaticPool
    )
else:
    # For PostgreSQL or other databases (production):
    engine = create_engine(DATABASE_URL)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create base class for models
Base = declarative_base()

# Define database models
class TranscriptModel(Base):
    """SQLAlchemy model for storing user-contributed transcripts"""
    __tablename__ = "transcripts"
    
    id = Column(String, primary_key=True, index=True)
    video_id = Column(String, index=True, nullable=False)
    video_title = Column(String, nullable=False)
    transcript_text = Column(Text, nullable=False)
    contributor_name = Column(String, nullable=True)
    contributor_email = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    upvotes = Column(Integer, default=0)
    is_approved = Column(Boolean, default=False)
    
# Create all tables
def init_db():
    """Initialize the database by creating all defined tables"""
    logger.info("Initializing database...")
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created successfully")
    except Exception as e:
        logger.error(f"Error creating database tables: {str(e)}")
        raise

# Function to get a database session
def get_db():
    """Get a database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close() 