from youtube_transcript_api import YouTubeTranscriptApi
import sys

def test_transcript(video_id):
    """Test fetching a transcript for a video ID"""
    print(f"Testing transcript fetch for video ID: {video_id}")
    try:
        transcript = YouTubeTranscriptApi.get_transcript(video_id)
        print(f"Success! Found {len(transcript)} transcript segments")
        print("First few segments:")
        for i, segment in enumerate(transcript[:3]):
            print(f"{i+1}. {segment['text']}")
        return True
    except Exception as e:
        print(f"Error: {type(e).__name__}: {str(e)}")
        return False

if __name__ == "__main__":
    # Test with a few known videos
    test_videos = [
        "8S0FDjFBj8o",  # TED Talk - should have transcript
        "dQw4w9WgXcQ",  # Rick Roll - popular video, should have transcript
        "yZYQpge1W5s",  # Random cooking video - should have transcript
    ]
    
    # Add command line argument if provided
    if len(sys.argv) > 1:
        test_videos.insert(0, sys.argv[1])
    
    success_count = 0
    for video_id in test_videos:
        print("\n" + "="*50)
        if test_transcript(video_id):
            success_count += 1
    
    print("\n" + "="*50)
    print(f"Results: {success_count}/{len(test_videos)} videos had accessible transcripts") 