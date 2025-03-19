import re
import logging
import json
import requests
from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled, NoTranscriptFound

# Set up logging
logger = logging.getLogger(__name__)

def extract_video_id(url: str) -> str:
    """
    Extract YouTube video ID from URL
    
    Supports formats:
    - youtube.com/watch?v=VIDEO_ID
    - youtu.be/VIDEO_ID
    - youtu.be/VIDEO_ID?si=...
    - youtube.com/embed/VIDEO_ID
    """
    # Patterns for YouTube URLs with better handling of query parameters
    try:
        # Short URL format (youtu.be/ID?parameters)
        if 'youtu.be/' in url:
            # Find the position after youtu.be/
            start_pos = url.find('youtu.be/') + len('youtu.be/')
            # Either find the next ? or take until the end
            if '?' in url[start_pos:]:
                end_pos = url.find('?', start_pos)
                video_id = url[start_pos:end_pos]
            else:
                video_id = url[start_pos:]
                
            # Verify it's 11 characters
            if len(video_id) == 11:
                logger.info(f"Extracted video ID '{video_id}' from short URL")
                return video_id
                
        # Watch URL format (youtube.com/watch?v=ID&parameters)
        elif 'youtube.com/watch' in url and 'v=' in url:
            # Find v= parameter
            start_pos = url.find('v=') + len('v=')
            # Either find the next & or take until the end
            if '&' in url[start_pos:]:
                end_pos = url.find('&', start_pos)
                video_id = url[start_pos:end_pos]
            else:
                video_id = url[start_pos:]
                
            # Verify it's 11 characters
            if len(video_id) == 11:
                logger.info(f"Extracted video ID '{video_id}' from watch URL")
                return video_id
                
        # Embed URL format
        elif 'youtube.com/embed/' in url:
            # Find the position after youtube.com/embed/
            start_pos = url.find('youtube.com/embed/') + len('youtube.com/embed/')
            # Either find the next ? or take until the end
            if '?' in url[start_pos:]:
                end_pos = url.find('?', start_pos)
                video_id = url[start_pos:end_pos]
            else:
                video_id = url[start_pos:]
                
            # Verify it's 11 characters
            if len(video_id) == 11:
                logger.info(f"Extracted video ID '{video_id}' from embed URL")
                return video_id
                
        # Fallback to regex pattern for other formats
        patterns = [
            r'(?:youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/embed\/)([a-zA-Z0-9_-]{11})'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                logger.info(f"Extracted video ID '{match.group(1)}' using regex")
                return match.group(1)
            
        # If we get here, none of the extraction methods worked
        raise ValueError("Failed to extract video ID from URL")
    
    except Exception as e:
        logger.error(f"Error extracting video ID: {str(e)}")
        raise ValueError(f"Invalid YouTube URL format: {str(e)}")

def get_transcript_with_alternative_api(video_id: str) -> str:
    """
    Alternative transcript fetcher using backend.js.org API
    """
    try:
        logger.info(f"Trying alternative API for video ID: {video_id}")
        api_url = f"https://tube.demarches.tech/api/v1/captions/{video_id}"
        response = requests.get(api_url, timeout=10)
        
        if response.status_code != 200:
            logger.error(f"Alternative API error: {response.status_code} - {response.text}")
            raise ValueError(f"Alternative API returned status {response.status_code}")
            
        data = response.json()
        
        # Check if captions are available
        if not data or "description" not in data or not data["description"]:
            logger.error("Alternative API returned no captions")
            raise ValueError("No captions found in alternative API response")
            
        # The API returns the full transcript in the description field
        transcript_text = data["description"]
        logger.info(f"Successfully retrieved transcript from alternative API: {len(transcript_text)} chars")
        return transcript_text
    except Exception as e:
        logger.error(f"Alternative API error: {str(e)}")
        raise ValueError(f"Alternative API error: {str(e)}")

def get_youtube_transcript(url: str) -> dict:
    """
    Get transcript from YouTube video
    
    Args:
        url: YouTube video URL
        
    Returns:
        Dictionary containing transcript text and video ID
    """
    video_id = None
    
    try:
        # Extract video ID from URL
        video_id = extract_video_id(url)
        logger.info(f"Extracted video ID: {video_id} from URL: {url}")
        
        try:
            # First attempt: Try to get transcript with default settings
            logger.info(f"Attempting to get transcript for video ID: {video_id}")
            transcript_list = YouTubeTranscriptApi.get_transcript(video_id)
            logger.info(f"Successfully retrieved transcript with {len(transcript_list)} entries")
            
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
        except Exception as e:
            # First attempt failed, log the error
            logger.error(f"Error getting transcript: {str(e)}")
            
            # Second attempt: Try with English language code explicitly
            logger.info("Trying to get transcript with language code 'en'")
            try:
                transcript_list = YouTubeTranscriptApi.get_transcript(video_id, languages=['en'])
                logger.info(f"Successfully retrieved English transcript with {len(transcript_list)} entries")
                
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
            except Exception as e2:
                logger.error(f"Error getting transcript with language code: {str(e2)}")
                
                # Third attempt: Try getting all available transcripts and selecting the first one
                logger.info("Trying to list all available transcripts")
                try:
                    transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
                    first_transcript = next(iter(transcript_list))
                    logger.info(f"Found transcript in language: {first_transcript.language}")
                    transcript_list = first_transcript.fetch()
                    logger.info(f"Successfully retrieved transcript in {first_transcript.language}")
                    
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
                except Exception as e3:
                    logger.error(f"All standard transcript retrieval methods failed: {str(e3)}")
                    
                    # Last attempt: Try alternative API
                    logger.info("Trying alternative API as final fallback")
                    try:
                        transcript_text = get_transcript_with_alternative_api(video_id)
                        return {
                            "transcript": transcript_text,
                            "video_id": video_id
                        }
                    except Exception as e4:
                        logger.error(f"Alternative API fallback failed: {str(e4)}")
                        raise ValueError("No transcript available for this video after all attempts. This video likely doesn't have captions enabled.")
    
    except TranscriptsDisabled:
        logger.error(f"TranscriptsDisabled error for video ID: {video_id}")
        
        # Try alternative API as a last resort
        try:
            transcript_text = get_transcript_with_alternative_api(video_id)
            return {
                "transcript": transcript_text,
                "video_id": video_id
            }
        except Exception as alt_error:
            logger.error(f"Alternative API failed after TranscriptsDisabled: {str(alt_error)}")
            raise ValueError("Transcripts are disabled for this video and alternative methods failed.")
            
    except NoTranscriptFound:
        logger.error(f"NoTranscriptFound error for video ID: {video_id}")
        
        # Try alternative API as a last resort
        try:
            transcript_text = get_transcript_with_alternative_api(video_id)
            return {
                "transcript": transcript_text,
                "video_id": video_id
            }
        except Exception as alt_error:
            logger.error(f"Alternative API failed after NoTranscriptFound: {str(alt_error)}")
            raise ValueError("No transcript found for this video. It might not have captions available.")
            
    except ValueError as ve:
        # Pass through any ValueError we raised ourselves
        logger.error(f"ValueError: {str(ve)}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        raise ValueError(f"Error fetching transcript: {str(e)}") 