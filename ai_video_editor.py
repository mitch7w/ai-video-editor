from dotenv import load_dotenv
from openai import OpenAI
import os
import ffmpeg
import json

load_dotenv()
client = OpenAI()

# load mp3s

# Define the input video files
video_files = [
    'update.mp4',
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

transcriptions = []

# now get transcriptions from whisper
for temp_file in temp_files:
    audio_file = open(temp_file, "rb")
    transcript = client.audio.transcriptions.create(
        file=audio_file,
        model="whisper-1",
        response_format="verbose_json",
        timestamp_granularities=["word"]
    )
    transcriptions.append(transcript)

# Create a single string with filenames and their corresponding transcriptions
transcription_strings = ", ".join(
    f"{video_files[idx]}: {transcription}" for idx, transcription in enumerate(transcriptions)
)

print("transcription_strings: ", transcription_strings)

# now actually perform editing process with GPT-4o

system_prompt = ''' You are an expert video editor who is given the transcriptions of video files and then returns a json object of which seconds of which video to stitch together in what order. You may combine the videos in any order so long as the output is coherent, not repetitive and flows naturally. If sentences are restarted by the speaker please do not include repeated phrases but rather only use the later corrected version of the sentence. Extract the words and sentences you desire from the input transcription and then output the ordered json based on this desired_transcription. Ensure that the start of words or sentences are not cut off by cutting one or two frames just before the next word starts. Do not make very small cuts where you only cut out less than a second of video as this is very choppy and undesirable. Please cut out large periods of silence. Use the exact seconds and milliseconds values given to you in the transcriptions. Do not add words to the transcription but ONLY extract desired words from the transcription given to you. For a given transcription input like this: update.mp4: Transcription(text="Hey, what's up? So it is Tuesday afternoon, and I've had a pretty productive day so far. Uhhhhhh. Hey, what's up it is Tuesday afternoon...", task='transcribe', language='english', duration=136.92999267578125, words=[{'word': 'Hey', 'start': 1.159999966621399, 'end': 1.6799999475479126}, {'word': "what's", 'start': 1.6799999475479126, 'end': 1.8600000143051147}... {'word': "Hey", 'start':4.5749999475479126, 'end': 4.600000143051147}" the output should be 
    {
    desired_transcription: "Hey what's up it is Tuesday afternoon...",
    videos: [{'file': 'input1.mp4', 'start': 4.5749999475479126, 'end': 10.000573},
    {'file': 'input2.mp4', 'start': 5.48509, 'end': 15.461233},
    {'file': 'input1.mp4', 'start': 11.1204836, 'end': 13.98464},
    {'file': 'input3.mp4', 'start': 2.22986001, 'end': 8.90233} ] 
    }
    Thus the repeated sentence is cut out and the exact seconds values are used.
'''

response = client.chat.completions.create(
    model="gpt-4o",
    response_format={"type": "json_object"},
    messages=[
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": transcription_strings}
    ]
)

editing_instructions_json = json.loads(response.choices[0].message.content)

# Clean up temporary files if needed
for temp_file in temp_files:
    os.remove(temp_file)

# perform editing now

edited_script = editing_instructions_json['desired_transcription']
video_files = editing_instructions_json['videos']

print("edited_script: ", edited_script)
print("video_files: ", video_files)

# Create a list of ffmpeg inputs with specified start and end times
inputs = [ffmpeg.input(video['file'], ss=video['start'],
                       to=video['end']) for video in video_files]

# Create a list of tuples, each containing the video and audio streams of a file
stream_pairs = [(input.video, input.audio) for input in inputs]

# Concatenate the video clips
if stream_pairs:
    concat = ffmpeg.concat(
        *[item for sublist in stream_pairs for item in sublist], v=1, a=1).node
    output = ffmpeg.output(concat[0], concat[1], 'ai_output.mp4')
    output.run()

print("Video concatenation complete. Output saved as 'ai_output.mp4'.")

# TODO problem is with GPT call. Change prompt and give one shot example.
