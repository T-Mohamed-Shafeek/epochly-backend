from fastapi import FastAPI, HTTPException, Depends, Header, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List, Optional
import os
import logging
from dotenv import load_dotenv
from sqlalchemy.orm import Session

from app.services.youtube_service import get_youtube_transcript
from app.services.llm_service import generate_summary, generate_mcqs
from app.services.transcript_service import (
    create_transcript, 
    get_transcript_by_video_id,
    upvote_transcript,
    get_all_transcripts_for_video
)
from app.models.database import get_db, init_db
from app.models.transcript import TranscriptCreate, Transcript, TranscriptVote

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

app = FastAPI(
    title="Epochly Backend API",
    description="Backend API for Epochly learning platform",
    version="1.0.0"
)

# Configure CORS - make it more permissive for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins in development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize the database on startup
@app.on_event("startup")
async def startup_event():
    init_db()
    logger.info("Database initialized on startup")

# Request and Response Models
class TranscriptRequest(BaseModel):
    url: str
    instructions: Optional[str] = None

class TranscriptResponse(BaseModel):
    success: bool
    transcript: str
    summary: Optional[str] = None
    video_id: str

class QuizQuestion(BaseModel):
    question: str
    options: List[str]
    correctAnswer: str
    explanation: Optional[str] = None

class QuizRequest(BaseModel):
    transcript: str
    numQuestions: Optional[int] = 5

class QuizResponse(BaseModel):
    questions: List[QuizQuestion]

# Dependency for API Key validation
def get_api_credentials(
    x_api_key: Optional[str] = Header(None),
    x_api_provider: Optional[str] = Header(None)
):
    if not x_api_key or not x_api_provider:
        raise HTTPException(
            status_code=401,
            detail="API Key and Provider are required"
        )
    
    if x_api_provider.lower() != "groq":
        raise HTTPException(
            status_code=400,
            detail="Currently only Groq is supported as an API provider"
        )
    
    return {"api_key": x_api_key, "api_provider": x_api_provider}

# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Global exception handler caught: {str(exc)}")
    return JSONResponse(
        status_code=500,
        content={"detail": f"Internal server error: {str(exc)}"},
    )

# API Routes
@app.get("/")
async def root():
    return {"message": "Welcome to Epochly Backend API"}

@app.post("/api/transcript", response_model=TranscriptResponse)
async def fetch_transcript(
    request: TranscriptRequest,
    credentials: dict = Depends(get_api_credentials),
    db: Session = Depends(get_db)
):
    try:
        logger.info(f"Processing transcript request for URL: {request.url}")
        
        try:
            # Get transcript from YouTube
            transcript_result = get_youtube_transcript(request.url)
            logger.info(f"Successfully retrieved transcript for video ID: {transcript_result['video_id']}")
        except ValueError as youtube_error:
            # If YouTube transcript retrieval fails, try getting from our database
            video_id = request.url.split("v=")[-1].split("&")[0] if "v=" in request.url else request.url.split("/")[-1].split("?")[0]
            logger.info(f"YouTube transcript failed, trying user-contributed transcript for video ID: {video_id}")
            
            # Check for user-contributed transcript
            db_transcript = get_transcript_by_video_id(db, video_id)
            if db_transcript:
                logger.info(f"Found user-contributed transcript for video ID: {video_id}")
                transcript_result = {
                    "transcript": db_transcript.transcript_text,
                    "video_id": video_id
                }
            else:
                # If no user transcript either, re-raise the original error
                logger.error(f"No transcript available from any source: {str(youtube_error)}")
                raise youtube_error
        
        # Generate summary if requested
        summary = None
        if request.instructions:
            logger.info("Generating summary with instructions")
            summary = await generate_summary(
                transcript_result["transcript"], 
                credentials["api_key"],
                request.instructions
            )
            logger.info("Summary generated successfully")
        
        return {
            "success": True,
            "transcript": transcript_result["transcript"],
            "summary": summary,
            "video_id": transcript_result["video_id"]
        }
    except ValueError as e:
        logger.error(f"ValueError in fetch_transcript: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error in fetch_transcript: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Server error: {str(e)}")

@app.post("/api/youtube/generate-quiz", response_model=QuizResponse)
async def generate_quiz(
    request: QuizRequest,
    credentials: dict = Depends(get_api_credentials)
):
    try:
        logger.info(f"Generating quiz with {request.numQuestions} questions")
        questions = await generate_mcqs(
            request.transcript, 
            credentials["api_key"], 
            request.numQuestions
        )
        logger.info(f"Successfully generated {len(questions)} questions")
        return {"questions": questions}
    except Exception as e:
        logger.error(f"Error in generate_quiz: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

# User-contributed transcript endpoints
@app.post("/api/transcripts/contribute", response_model=Transcript)
async def contribute_transcript(
    transcript: TranscriptCreate,
    db: Session = Depends(get_db)
):
    """
    Submit a user-contributed transcript
    """
    try:
        logger.info(f"User contributing transcript for video ID: {transcript.video_id}")
        result = create_transcript(db, transcript)
        logger.info(f"Successfully saved user-contributed transcript with ID: {result.id}")
        
        return result
    except Exception as e:
        logger.error(f"Error in contribute_transcript: {str(e)}")
        raise HTTPException(status_code=400, detail=f"Failed to save transcript: {str(e)}")

@app.get("/api/transcripts/{video_id}", response_model=List[Transcript])
async def get_transcripts(
    video_id: str,
    db: Session = Depends(get_db)
):
    """
    Get all user-contributed transcripts for a video
    """
    try:
        logger.info(f"Getting all transcripts for video ID: {video_id}")
        transcripts = get_all_transcripts_for_video(db, video_id)
        logger.info(f"Found {len(transcripts)} transcripts for video ID: {video_id}")
        
        return transcripts
    except Exception as e:
        logger.error(f"Error in get_transcripts: {str(e)}")
        raise HTTPException(status_code=400, detail=f"Failed to retrieve transcripts: {str(e)}")

@app.post("/api/transcripts/upvote", response_model=dict)
async def upvote_transcript_endpoint(
    vote: TranscriptVote,
    db: Session = Depends(get_db)
):
    """
    Upvote a transcript
    """
    try:
        logger.info(f"Upvoting transcript ID: {vote.transcript_id}")
        success = upvote_transcript(db, vote.transcript_id)
        
        if not success:
            raise HTTPException(status_code=404, detail="Transcript not found")
            
        return {"success": True, "message": "Transcript upvoted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in upvote_transcript: {str(e)}")
        raise HTTPException(status_code=400, detail=f"Failed to upvote transcript: {str(e)}")

# For direct execution
if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    host = os.getenv("HOST", "0.0.0.0")
    uvicorn.run("app.main:app", host=host, port=port, reload=True) 