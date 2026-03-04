from youtube_transcript_api import YouTubeTranscriptApi

# Replace with the video ID you're testing (the part after ?v=)
vid_id = "dQw4w9WgXcQ"

ytt = YouTubeTranscriptApi()

try:
    transcript_list = ytt.list_transcripts(vid_id)
    print("Available transcripts:")
    for t in transcript_list:
        print(f"  - {t.language} ({t.language_code}) | generated: {t.is_generated}")
    
    transcript = transcript_list.find_transcript(['en'])
    data = transcript.fetch()
    print(f"\nSuccess! Got {len(data)} segments.")
    print("First line:", data[0].text)

except Exception as e:
    print(f"ERROR: {type(e).__name__}: {e}")
