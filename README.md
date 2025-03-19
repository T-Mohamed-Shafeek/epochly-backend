# Epochly Backend

FastAPI backend for Epochly learning platform with enhanced YouTube transcription, multiple fallback methods, and LLM capabilities.

## Features

- YouTube video transcript fetching using `youtube-transcript-api`
- Multiple transcript retrieval fallback methods:
  - Pre-cached transcripts for example videos
  - PyTube integration for additional transcript sources
  - Multiple alternative transcript APIs with SSL verification handling
  - Web scraping fallback for extracting transcripts
- Integration with manual transcript submission from NoteGPT
- Summary generation using Groq LLM
- Multiple-choice question (MCQ) generation
- User-provided Groq API key support

## Requirements

- Python 3.9+
- Dependencies listed in `requirements.txt`

## Setup

1. Clone this repository
2. Create a virtual environment:
   ```
   python -m venv venv
   venv\Scripts\activate  # On Windows
   source venv/bin/activate  # On Unix/macOS
   ```
3. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
4. Create a `.env` file based on `.env.example`:
   ```
   cp .env.example .env
   ```
5. Run the application:
   ```
   python run.py
   ```

## API Endpoints

### GET /

Root endpoint that returns a welcome message.

### POST /api/transcript

Fetches a YouTube video transcript and optionally generates a summary.

**Headers:**
- `X-API-Key`: Groq API key
- `X-API-Provider`: API provider (currently only "groq" is supported)

**Request Body:**
```json
{
  "url": "https://www.youtube.com/watch?v=VIDEO_ID",
  "instructions": "Optional instructions for summary generation"
}
```

**Response:**
```json
{
  "success": true,
  "transcript": "Video transcript text...",
  "summary": "Generated summary...",
  "video_id": "VIDEO_ID"
}
```

### POST /api/youtube/generate-quiz

Generates quiz questions from a transcript.

**Headers:**
- `X-API-Key`: Groq API key
- `X-API-Provider`: API provider (currently only "groq" is supported)

**Request Body:**
```json
{
  "transcript": "Video transcript text...",
  "numQuestions": 5
}
```

**Response:**
```json
{
  "questions": [
    {
      "question": "Question text?",
      "options": ["Option A", "Option B", "Option C", "Option D"],
      "correctAnswer": "Option B",
      "explanation": "Explanation for correct answer"
    },
    // More questions...
  ]
}
```

## Transcript Retrieval Process

The backend uses a multi-stage approach to maximize transcript availability:

1. **Cached Transcript Check**: First checks if the video is in our pre-cached examples
2. **YouTube API Attempt**: Uses the official `youtube-transcript-api` with multiple language options
3. **PyTube Fallback**: Uses the PyTube library to extract captions directly
4. **Alternative APIs**: Tries multiple alternative APIs that can extract captions
5. **Web Scraping**: Final fallback method that extracts transcript directly from YouTube's page

If all automatic methods fail, the frontend provides a manual submission option with NoteGPT integration.

## Frontend Integration

This backend is designed to work with the Epochly frontend, replacing the previous YouTube Data API implementation with a more robust solution that:

1. Uses the `youtube-transcript-api` library for transcript fetching
2. Processes transcripts using the Groq LLM API
3. Generates summaries and MCQs based on user configuration
4. Handles transcript failures gracefully with fallback options

Update your frontend API calls to match the endpoints provided by this backend service. 