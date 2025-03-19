from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
import uuid

class TranscriptBase(BaseModel):
    """Base model for transcript data"""
    video_id: str
    video_title: str
    transcript_text: str
    
class TranscriptCreate(TranscriptBase):
    """Model for creating a new transcript"""
    contributor_name: Optional[str] = None
    contributor_email: Optional[str] = None
    
class Transcript(TranscriptBase):
    """Model for a transcript with metadata"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    contributor_name: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    upvotes: int = 0
    is_approved: bool = False
    
    class Config:
        orm_mode = True
        
class TranscriptVote(BaseModel):
    """Model for voting on transcripts"""
    transcript_id: str 