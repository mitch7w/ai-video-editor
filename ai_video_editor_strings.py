from string import ascii_letters
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
temp_mp3_files = []
transcriptions = []

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
    transcription_strings = ""
    for each in transcriptions:
        transcription_strings += each['video']
        transcription_strings += ": "
        transcription_strings += each['transcription_object'].text
        transcription_strings += ", "

print("transcription_strings: ", transcription_strings)

# now actually perform editing process with GPT-4o

system_prompt = ''' You are an expert video editor who is given the transcript of an unedited video file and then returns the transcript of the edited video that cuts out repeated sentences, mistakes or unimportant parts. Please do not add words or punctuation - only use the exact transcription given to you and extract words from it as substring methods will be used to actually edit the videos. For example an input might be "Hey, what's up? So it is Tuesday afternoon, and I've had a pretty productive day so far. I've just been working on my AI video generator, which is quite cool. It's doing, hey, what's up? So I've been working on my AI video generator this afternoon. There is a, uhm. I want to show you what I've been working on today." and the output would be:
{
    edits: ["hey, what's up? So I've been working on my AI video generator this afternoon.",
        "I want to show you what I've been working on today."]
}
 Please only output the edited text in json format, starting a new array element when the output becomes discontinuous from the original transcription.
'''

response = client.chat.completions.create(
    model="gpt-4o",
    response_format={"type": "json_object"},
    messages=[
        {"role": "system", "content": system_prompt},
        {"role": "user",
            "content": transcriptions[0]['transcription_object'].text}
    ]
)
print("GPT Response 1 ",
      response.choices[0].message.content)
edited_json = json.loads(response.choices[0].message.content)
edited_texts_array = edited_json['edits']
print("edited_texts_array: ", edited_texts_array)

def find_substring_indices(main_string, substring):
    # Find the start index of the substring
    start_index = main_string.lower().find(substring.lower())

    if start_index == -1:
        # Substring not found
        return 0, 0

    # Calculate the end index based on the start index and the length of the substring
    end_index = start_index + len(substring) - 1

    return start_index, end_index


editing_instructions = []

for edit in edited_texts_array:
    start_index, end_index = find_substring_indices(
        transcriptions[0]['transcription_object'].text, edit)
    # indices are inside substring - convert to words time
    editing_instructions.append({"file": "update.mp4", "start": transcriptions[0]['transcription_object'].words[
                                start_index], "end": transcriptions[0]['transcription_object'].words[end_index]})
  ````  print("start_time, end_time: ", start_index, end_index)


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

# TODO problem is with GPT call. Change prompt and give one shot example.
# TODO test just moving system prompt to user prompt but i doubt it and this is more finegraned anyway
