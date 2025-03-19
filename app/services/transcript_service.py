import logging
from sqlalchemy.orm import Session
from app.models.database import TranscriptModel
from app.models.transcript import TranscriptCreate, Transcript
import uuid
from datetime import datetime

# Set up logging
logger = logging.getLogger(__name__)

def create_transcript(db: Session, transcript: TranscriptCreate) -> Transcript:
    """
    Save a new user-contributed transcript to the database
    
    Args:
        db: Database session
        transcript: Transcript data to save
        
    Returns:
        Saved transcript with metadata
    """
    try:
        # Create a new transcript model
        db_transcript = TranscriptModel(
            id=str(uuid.uuid4()),
            video_id=transcript.video_id,
            video_title=transcript.video_title,
            transcript_text=transcript.transcript_text,
            contributor_name=transcript.contributor_name,
            contributor_email=transcript.contributor_email,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            upvotes=0,
            is_approved=False  # New transcripts need approval
        )
        
        # Add to database and commit
        db.add(db_transcript)
        db.commit()
        db.refresh(db_transcript)
        
        logger.info(f"Created new transcript for video ID: {transcript.video_id}")
        
        # Convert to Pydantic model and return
        return Transcript(
            id=db_transcript.id,
            video_id=db_transcript.video_id,
            video_title=db_transcript.video_title,
            transcript_text=db_transcript.transcript_text,
            contributor_name=db_transcript.contributor_name,
            created_at=db_transcript.created_at,
            updated_at=db_transcript.updated_at,
            upvotes=db_transcript.upvotes,
            is_approved=db_transcript.is_approved
        )
    except Exception as e:
        logger.error(f"Error creating transcript: {str(e)}")
        db.rollback()
        raise

def get_transcript_by_video_id(db: Session, video_id: str) -> Transcript:
    """
    Get a transcript for a specific video ID
    
    Args:
        db: Database session
        video_id: YouTube video ID
        
    Returns:
        Transcript if found, None otherwise
    """
    try:
        # Query for approved transcripts for this video ID, order by upvotes
        db_transcript = db.query(TranscriptModel).filter(
            TranscriptModel.video_id == video_id,
            TranscriptModel.is_approved == True
        ).order_by(TranscriptModel.upvotes.desc()).first()
        
        if not db_transcript:
            logger.info(f"No approved transcript found for video ID: {video_id}")
            return None
            
        logger.info(f"Found transcript for video ID: {video_id}")
        
        # Convert to Pydantic model and return
        return Transcript(
            id=db_transcript.id,
            video_id=db_transcript.video_id,
            video_title=db_transcript.video_title,
            transcript_text=db_transcript.transcript_text,
            contributor_name=db_transcript.contributor_name,
            created_at=db_transcript.created_at,
            updated_at=db_transcript.updated_at,
            upvotes=db_transcript.upvotes,
            is_approved=db_transcript.is_approved
        )
    except Exception as e:
        logger.error(f"Error retrieving transcript: {str(e)}")
        raise

def upvote_transcript(db: Session, transcript_id: str) -> bool:
    """
    Upvote a transcript
    
    Args:
        db: Database session
        transcript_id: ID of the transcript to upvote
        
    Returns:
        True if successful, False otherwise
    """
    try:
        # Find the transcript
        db_transcript = db.query(TranscriptModel).filter(
            TranscriptModel.id == transcript_id
        ).first()
        
        if not db_transcript:
            logger.warning(f"Transcript not found for upvote: {transcript_id}")
            return False
            
        # Increment upvotes
        db_transcript.upvotes += 1
        db.commit()
        
        logger.info(f"Upvoted transcript {transcript_id} to {db_transcript.upvotes} upvotes")
        return True
    except Exception as e:
        logger.error(f"Error upvoting transcript: {str(e)}")
        db.rollback()
        return False

def get_all_transcripts_for_video(db: Session, video_id: str):
    """
    Get all transcripts for a specific video ID
    
    Args:
        db: Database session
        video_id: YouTube video ID
        
    Returns:
        List of transcripts
    """
    try:
        # Query for all approved transcripts for this video ID, order by upvotes
        db_transcripts = db.query(TranscriptModel).filter(
            TranscriptModel.video_id == video_id,
            TranscriptModel.is_approved == True
        ).order_by(TranscriptModel.upvotes.desc()).all()
        
        logger.info(f"Found {len(db_transcripts)} transcripts for video ID: {video_id}")
        
        # Convert to Pydantic models and return
        return [
            Transcript(
                id=t.id,
                video_id=t.video_id,
                video_title=t.video_title,
                transcript_text=t.transcript_text,
                contributor_name=t.contributor_name,
                created_at=t.created_at,
                updated_at=t.updated_at,
                upvotes=t.upvotes,
                is_approved=t.is_approved
            ) for t in db_transcripts
        ]
    except Exception as e:
        logger.error(f"Error retrieving transcripts: {str(e)}")
        raise 