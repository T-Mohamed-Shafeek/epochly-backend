import re
import logging
import json
import requests
from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled, NoTranscriptFound
import time
import urllib3
from bs4 import BeautifulSoup

# Suppress SSL verification warning
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Import pytube for additional transcript retrieval method
try:
    from pytube import YouTube
    PYTUBE_AVAILABLE = True
except ImportError:
    PYTUBE_AVAILABLE = False
    logging.warning("pytube library not available - this fallback method won't be used")

# Import BeautifulSoup for web scraping fallback
try:
    from bs4 import BeautifulSoup
    BEAUTIFULSOUP_AVAILABLE = True
except ImportError:
    BEAUTIFULSOUP_AVAILABLE = False
    logging.warning("BeautifulSoup library not available - webscraping fallback won't be used")

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

def get_transcript_with_pytube(video_id: str) -> str:
    """
    Attempt to get transcript using pytube library
    """
    if not PYTUBE_AVAILABLE:
        raise ValueError("pytube library not available")
        
    try:
        logger.info(f"Trying pytube for video ID: {video_id}")
        youtube_url = f"https://www.youtube.com/watch?v={video_id}"
        
        # Add retry logic with backoff
        max_retries = 3
        retry_delay = 2
        
        for attempt in range(max_retries):
            try:
                yt = YouTube(youtube_url)
                break
            except Exception as e:
                if attempt == max_retries - 1:
                    raise
                logger.warning(f"pytube connection error (attempt {attempt+1}/{max_retries}): {str(e)}")
                time.sleep(retry_delay)
                retry_delay *= 2
        
        # Get caption tracks
        caption_tracks = yt.captions
        
        if not caption_tracks or len(caption_tracks) == 0:
            logger.warning("No captions found using pytube")
            raise ValueError("No captions found using pytube")
            
        # Try to get English captions first
        caption = None
        for track in caption_tracks:
            if track.code.startswith('en'):
                caption = track
                break
                
        # If no English captions, use the first available
        if caption is None and len(caption_tracks) > 0:
            caption = list(caption_tracks.values())[0]
            
        if caption is None:
            raise ValueError("No usable captions found")
            
        # Get the transcript text
        transcript_xml = caption.xml_captions
        
        # Simple XML parsing to extract text
        transcript_text = ""
        import re
        text_parts = re.findall(r'<text[^>]*>(.*?)</text>', transcript_xml)
        
        for part in text_parts:
            # Remove XML entities and cleanup
            cleaned_part = part.replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>')
            transcript_text += cleaned_part + " "
            
        transcript_text = transcript_text.strip()
        
        if not transcript_text or len(transcript_text) < 50:
            raise ValueError("Retrieved transcript is too short or empty")
            
        logger.info(f"Successfully retrieved transcript using pytube: {len(transcript_text)} chars")
        return transcript_text
        
    except Exception as e:
        logger.error(f"pytube error: {str(e)}")
        raise ValueError(f"pytube error: {str(e)}")

def get_transcript_by_scraping(video_id: str) -> str:
    """
    Last resort method to attempt to extract transcript by scraping
    """
    if not BEAUTIFULSOUP_AVAILABLE:
        raise ValueError("BeautifulSoup library not available for web scraping")
        
    try:
        logger.info(f"Attempting to get transcript via web scraping for video ID: {video_id}")
        
        # Try to get the page with transcript data
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        youtube_url = f"https://www.youtube.com/watch?v={video_id}"
        
        # Try with a timeout and retry logic
        max_retries = 2
        retry_delay = 1
        
        for attempt in range(max_retries):
            try:
                response = requests.get(youtube_url, headers=headers, timeout=10)
                break
            except Exception as e:
                if attempt == max_retries - 1:
                    raise
                logger.warning(f"Scraping connection error (attempt {attempt+1}/{max_retries}): {str(e)}")
                time.sleep(retry_delay)
                retry_delay *= 2
        
        if response.status_code != 200:
            raise ValueError(f"Failed to fetch YouTube page: {response.status_code}")
            
        # Parse the page
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Look for transcript data in the page
        # This is a simplistic approach and may break if YouTube changes their structure
        transcript_text = ""
        
        # Try to find script tags with JSON data
        for script_tag in soup.find_all('script'):
            if script_tag.string and "captionTracks" in script_tag.string:
                script_content = script_tag.string
                
                # Extract captionTracks
                caption_tracks_start = script_content.find("\"captionTracks\":")
                if caption_tracks_start > -1:
                    # Find the end of the captionTracks array
                    caption_tracks_end = script_content.find("]", caption_tracks_start)
                    caption_tracks_data = script_content[caption_tracks_start:caption_tracks_end+1]
                    
                    # Try to extract baseUrl
                    base_url_match = re.search(r"\"baseUrl\":\"(.*?)\"", caption_tracks_data)
                    if base_url_match:
                        caption_url = base_url_match.group(1).replace("\\u0026", "&")
                        
                        # Fetch the caption file
                        try:
                            caption_response = requests.get(caption_url, timeout=10)
                            if caption_response.status_code == 200:
                                # Parse the XML
                                caption_soup = BeautifulSoup(caption_response.text, 'xml')
                                
                                # Extract text from each entry
                                for text_tag in caption_soup.find_all('text'):
                                    if text_tag.string:
                                        transcript_text += text_tag.string + " "
                                
                                if transcript_text:
                                    break
                        except Exception as e:
                            logger.error(f"Error fetching caption file: {str(e)}")
        
        # Check if we found any transcript text
        transcript_text = transcript_text.strip()
        if not transcript_text or len(transcript_text) < 50:
            # Try an alternative approach - look for transcript text in the page
            # This is also likely to break if YouTube changes their page structure
            transcript_sections = soup.find_all('div', {'class': 'segment-text'})
            if transcript_sections:
                for section in transcript_sections:
                    transcript_text += section.get_text() + " "
                    
        # Final check for transcript text
        transcript_text = transcript_text.strip()
        if not transcript_text or len(transcript_text) < 50:
            raise ValueError("Could not extract transcript via web scraping")
            
        logger.info(f"Successfully retrieved transcript via web scraping: {len(transcript_text)} chars")
        return transcript_text
        
    except Exception as e:
        logger.error(f"Web scraping error: {str(e)}")
        raise ValueError(f"Failed to extract transcript via web scraping: {str(e)}")

def get_transcript_with_alternative_api(video_id: str) -> str:
    """
    Alternative transcript fetcher using multiple fallback APIs
    """
    apis = [
        {
            "name": "tube.demarches.tech",
            "url": f"https://tube.demarches.tech/api/v1/captions/{video_id}",
            "extract": lambda data: data.get("description", "")
        },
        {
            "name": "inv.bp.mutahar.rocks",
            "url": f"https://inv.bp.mutahar.rocks/api/v1/captions/{video_id}",
            "extract": lambda data: data.get("description", "")
        },
        {
            "name": "vid.puffyan.us",
            "url": f"https://vid.puffyan.us/api/v1/videos/{video_id}?fields=captions",
            "extract": lambda data: "\n".join([cap.get("label", "") for cap in data.get("captions", [])])
        }
    ]
    
    last_error = None
    
    # First try pytube if available
    if PYTUBE_AVAILABLE:
        try:
            return get_transcript_with_pytube(video_id)
        except Exception as e:
            logger.warning(f"pytube fallback failed: {str(e)}")
            # Continue to other APIs
    
    for api in apis:
        try:
            logger.info(f"Trying {api['name']} API for video ID: {video_id}")
            
            # Disable SSL verification for these APIs as they often have self-signed certificates
            response = requests.get(api["url"], timeout=15, verify=False)
            
            if response.status_code != 200:
                logger.warning(f"{api['name']} API error: {response.status_code} - {response.text}")
                continue
                
            try:
                data = response.json()
            except json.JSONDecodeError:
                logger.warning(f"{api['name']} API returned invalid JSON")
                continue
                
            transcript_text = api["extract"](data)
            
            if not transcript_text or len(transcript_text) < 50:
                logger.warning(f"{api['name']} API returned empty or very short transcript")
                continue
                
            logger.info(f"Successfully retrieved transcript from {api['name']} API: {len(transcript_text)} chars")
            return transcript_text
            
        except Exception as e:
            logger.error(f"{api['name']} API error: {str(e)}")
            last_error = e
            continue
    
    # Final fallback - try web scraping if available
    if BEAUTIFULSOUP_AVAILABLE:
        try:
            return get_transcript_by_scraping(video_id)
        except Exception as e:
            logger.warning(f"Web scraping fallback failed: {str(e)}")
            # Continue to error
    
    # If we get here, all methods failed
    error_msg = f"All alternative APIs and fallbacks failed. Last error: {str(last_error)}"
    logger.error(error_msg)
    raise ValueError(error_msg)

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