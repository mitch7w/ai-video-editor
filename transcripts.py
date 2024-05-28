import os
import ffmpeg
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()
client = OpenAI()

# Define the input video files
video_files = [
    'vai_1.mp4',
    # 'vai_2.mp4',
    # 'vai_3.mp4',
    # Add more video files as needed
]

# Temporary files to store the MP3s
temp_files = []

# Convert the videos to MP3
for idx, video_file in enumerate(video_files):
    temp_file = f'temp_audio_{idx}.mp3'
    temp_files.append(temp_file)
    (
        ffmpeg
        .input(video_file)
        .output(temp_file, format='mp3')
        .run()
    )

print("MP4 to MP3 conversion complete. Temporary files:", temp_files)

# now get transcriptions from whisper
for temp_file in temp_files:
    audio_file = open(temp_file, "rb")
    transcript = client.audio.transcriptions.create(
        file=audio_file,
        model="whisper-1",
        response_format="verbose_json",
        timestamp_granularities=["word"]
    )
    print(transcript)
    print(transcript.words)


# Clean up temporary files if needed
for temp_file in temp_files:
    os.remove(temp_file)

print("Temporary files removed.")
