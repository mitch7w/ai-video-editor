from string import ascii_letters
from dotenv import load_dotenv
from openai import OpenAI
import os
import ffmpeg
import json

load_dotenv()
client = OpenAI()


# Define the input video files
video_files = [
    'mitch1.mp4', 'mitch2.mp4', 'mitch3.mp4'
    # Add more video files as needed
]

# Temporary files to store the MP3s
temp_mp3_files = []
transcriptions = []
simplified_words = []

# Convert the videos to MP3
for idx, video_file in enumerate(video_files):
    temp_file = f'temp_audio_{idx}.mp3'
    temp_mp3_files.append(temp_file)
    (
        ffmpeg
        .input(video_file)
        .output(temp_file, format='mp3')
        .run()
    )
    audio_file = open(temp_file, "rb")
    transcript = client.audio.transcriptions.create(
        file=audio_file,
        model="whisper-1",
        response_format="verbose_json",
        timestamp_granularities=["word"]
    )
    transcriptions.append(
        {"video": video_file, "transcription_object": transcript})

# Create a single string with filenames and their corresponding transcriptions
    file_string = video_file + ": "
    simplified_words.append(file_string)
    words_array = transcript.words
    for word in words_array:
        simplified_words.append({word['word'], word['start'], word['end']})

print("simplified_words: ", simplified_words)

# now actually perform editing process with GPT-4o

system_prompt = ''' You are an expert video editor tasked with creating a concise, coherent video from a transcript. You will receive an array of objects, each containing a word, its start time, and end time in milliseconds. Your goal is to create a JSON object specifying which words to include in the final edit.
Editing guidelines:
1. Use only words provided in the input array.
2. Maintain logical flow and context in the edited video.
3. Remove repeated sentences, keeping the latter instance if it seems more polished.
4. Eliminate false starts and filler words that don't contribute to the message. For example if in the transcript you see the words "I... I am.... I am going to" remove the first two false starts and just include the timestamps from the beginning of the proper full sentence.
5. Cut out extended silences (>1 second) between words or sentences.
6. Ensure sentences are complete and not cut off mid-thought.
7. Add a small buffer (50-100ms) at the end of sentences for natural pacing.
8. Aim for a concise video while preserving the core message and context.
9. Ensure no single pause between words exceeds 500ms unless it's a natural break point. 
10. Check that you have not included false starts and only sentences that are finished properly by the speaker.
11. Return JSON and only JSON.
An example output might be:
    {
    desired_transcription: "hey, what's up? So I've been working on my AI video generator this afternoon. It's been going pretty well. And I've got the transcription working with Whisper in the background. I've got the cutting up and stitching together the final output done with FFmeg.",
    transcription_sources: [{'file': 'update.mp4', 'start': 9.2345322, 'end': 14.238438},
    {'file': 'update1.mp4', 'start': 20.4723769, 'end': 26.36824864},
    {'file': 'update1.mp4', 'start': 26.8723769, 'end': 29.9624864},
    {'file': 'update.mp4', 'start': 33.3444331, 'end': 48.3961112}
    }
'''

messages_history = []
# Add the system prompt first for OpenAI
messages_history.append({"role": "system", "content": system_prompt})
# Then add the user message with the transcript data
messages_history.append({"role": "user", "content": str(simplified_words)})

try:
    # OpenAI API Call
    completion = client.chat.completions.create(
        model="o3-mini",
        messages=messages_history,
        # Request JSON output if supported by the model version
        response_format={"type": "json_object"}
    )
    # Extract the response content
    response = completion.choices[0].message.content
    print("response: ", response)

except Exception as err:
    print(f"An error occurred with the OpenAI API call: {err}")

# print("OpenAI Response:", response) # Keep or remove this debugging line as needed
# Assuming the response is valid JSON as requested in the system prompt
edited_transcript_json = json.loads(response)
edited_script = edited_transcript_json['desired_transcription']
edited_transcription_sources = edited_transcript_json['transcription_sources']

print("Edited script: ", edited_script)
print("Edited transcription sources: ", edited_transcription_sources)


editing_instructions = edited_transcription_sources

# Clean up temporary files if needed
for temp_file in temp_mp3_files:
    os.remove(temp_file)

# perform editing now

# Create a list of ffmpeg inputs with specified start and end times
inputs = [ffmpeg.input(cut['file'], ss=cut['start'],
                       to=cut['end']) for cut in editing_instructions]

# Create a list of tuples, each containing the video and audio streams of a file
stream_pairs = [(input.video, input.audio) for input in inputs]

# Concatenate the video clips
if stream_pairs:
    concat = ffmpeg.concat(
        *[item for sublist in stream_pairs for item in sublist], v=1, a=1).node
    output = ffmpeg.output(concat[0], concat[1], 'ai_output.mp4')
    output.run()

print("Video concatenation complete. Output saved as 'ai_output.mp4'.")
