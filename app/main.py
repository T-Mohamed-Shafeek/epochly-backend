from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import os
from dotenv import load_dotenv
import logging

from app.services.youtube_service import get_youtube_transcript
from app.services.llm_service import generate_summary, generate_mcqs

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
        # Log the request information
        logging.info(f"Transcript request received for URL: {request.url}")
        logging.info(f"API Provider: {credentials['api_provider']}")
        logging.info(f"API Key present: {bool(credentials['api_key'])}")
        
        # Get transcript from YouTube
        try:
            transcript_result = get_youtube_transcript(request.url)
            logging.info(f"Transcript fetched successfully. Video ID: {transcript_result['video_id']}")
        except Exception as e:
            logging.error(f"Error fetching transcript: {str(e)}")
            raise HTTPException(status_code=400, detail=str(e))
        
        # Generate summary if requested
        summary = None
        if request.instructions:
            logging.info("Summary requested with instructions")
            try:
                summary = await generate_summary(
                    transcript_result["transcript"], 
                    credentials["api_key"],
                    request.instructions
                )
                logging.info("Summary generated successfully")
            except Exception as e:
                logging.error(f"Error generating summary: {str(e)}")
                # Don't fail the whole request if summary generation fails
                logging.info("Continuing with transcript only")
        
        return {
            "success": True,
            "transcript": transcript_result["transcript"],
            "summary": summary,
            "video_id": transcript_result["video_id"]
        }
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logging.exception("Unexpected error in fetch_transcript")
        raise HTTPException(status_code=500, detail=f"Server error: {str(e)}")

@app.post("/api/youtube/generate-quiz", response_model=QuizResponse)
async def generate_quiz(
    request: QuizRequest,
    credentials: dict = Depends(get_api_credentials)
):
    try:
        questions = await generate_mcqs(
            request.transcript, 
            credentials["api_key"], 
            request.numQuestions
        )
        return {"questions": questions}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# For direct execution
if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    host = os.getenv("HOST", "0.0.0.0")
    uvicorn.run("app.main:app", host=host, port=port, reload=True) 