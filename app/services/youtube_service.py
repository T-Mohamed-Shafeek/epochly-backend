from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled, NoTranscriptFound
import re

def extract_video_id(url: str) -> str:
    """
    Extract YouTube video ID from URL
    
    Supports formats:
    - youtube.com/watch?v=VIDEO_ID
    - youtu.be/VIDEO_ID
    - youtube.com/embed/VIDEO_ID
    """
    # Patterns for YouTube URLs
    youtube_patterns = [
        r'(?:youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/embed\/)([a-zA-Z0-9_-]{11})',
    ]
    
    for pattern in youtube_patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    
    raise ValueError("Invalid YouTube URL. Please provide a valid YouTube video URL.")

def get_youtube_transcript(url: str) -> dict:
    """
    Get transcript from YouTube video
    
    Args:
        url: YouTube video URL
        
    Returns:
        Dictionary containing transcript text and video ID
    """
    try:
        # Extract video ID from URL
        video_id = extract_video_id(url)
        
        # Get transcript from YouTube
        transcript_list = YouTubeTranscriptApi.get_transcript(video_id)
        
        # Combine transcript pieces into a single text
        transcript_text = ""
        for entry in transcript_list:
            transcript_text += entry['text'] + " "
        
        # Clean up the transcript
        transcript_text = transcript_text.strip()
        
        return {
            "transcript": transcript_text,
            "video_id": video_id
        }
    
    except TranscriptsDisabled:
        raise ValueError("Transcripts are disabled for this video.")
    except NoTranscriptFound:
        raise ValueError("No transcript found for this video. It might not have captions available.")
    except Exception as e:
        raise ValueError(f"Error fetching transcript: {str(e)}") 