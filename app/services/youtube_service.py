from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled, NoTranscriptFound
import re
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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
    
    logger.info(f"Extracting video ID from URL: {url}")
    
    for pattern in youtube_patterns:
        match = re.search(pattern, url)
        if match:
            video_id = match.group(1)
            logger.info(f"Successfully extracted video ID: {video_id}")
            return video_id
    
    logger.error(f"Failed to extract video ID from URL: {url}")
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
        
        logger.info(f"Fetching transcript for video ID: {video_id}")
        
        # Get transcript from YouTube
        try:
            transcript_list = YouTubeTranscriptApi.get_transcript(video_id)
            logger.info(f"Retrieved {len(transcript_list)} transcript entries")
        except Exception as e:
            logger.error(f"Error getting transcript: {str(e)}")
            # Try with language code
            try:
                logger.info("Trying to get transcript with language code 'en'")
                transcript_list = YouTubeTranscriptApi.get_transcript(video_id, languages=['en'])
                logger.info(f"Retrieved {len(transcript_list)} transcript entries with language code")
            except Exception as inner_e:
                logger.error(f"Error getting transcript with language code: {str(inner_e)}")
                raise
        
        # Combine transcript pieces into a single text
        transcript_text = ""
        for entry in transcript_list:
            transcript_text += entry['text'] + " "
        
        # Clean up the transcript
        transcript_text = transcript_text.strip()
        logger.info(f"Transcript processed. Length: {len(transcript_text)} characters")
        
        return {
            "transcript": transcript_text,
            "video_id": video_id
        }
    
    except TranscriptsDisabled:
        logger.error(f"Transcripts are disabled for video ID: {video_id}")
        raise ValueError("Transcripts are disabled for this video. Please try another video.")
    except NoTranscriptFound:
        logger.error(f"No transcript found for video ID: {video_id}")
        raise ValueError("No transcript found for this video. It might not have captions available.")
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        raise ValueError(f"Error fetching transcript: {str(e)}")