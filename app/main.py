from fastapi import FastAPI, HTTPException, Depends, Header, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List, Optional
import os
import logging
from dotenv import load_dotenv

from app.services.youtube_service import get_youtube_transcript
from app.services.llm_service import generate_summary, generate_mcqs

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
    credentials: dict = Depends(get_api_credentials)
):
    try:
        logger.info(f"Processing transcript request for URL: {request.url}")
        
        # Get transcript from YouTube
        transcript_result = get_youtube_transcript(request.url)
        logger.info(f"Successfully retrieved transcript for video ID: {transcript_result['video_id']}")
        
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

# For direct execution
if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    host = os.getenv("HOST", "0.0.0.0")
    uvicorn.run("app.main:app", host=host, port=port, reload=True) 