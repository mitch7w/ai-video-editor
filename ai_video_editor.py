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

system_prompt = ''' You are an expert video editor who is given the transcriptions of video files and then returns a json object of which transcriptions of which video to stitch together in what order. Please combine videos by extracting the exact words you want in the edited version from the transcriptions. Do not add words - only use those given to you alongside their origin video. Edit out repeated sentences and false starts so the video is concise and follows a natural script. For example an output could be:
    {
    desired_transcription: "Hey what's up it is Tuesday afternoon. I am working on a new version of my website this week. And that's why I am so excited about this new project.",
    transcription_sources: [{'file': 'input1.mp4', 'text': 'Hey what's up it is Tuesday afternoon.'},
    {'file': 'input2.mp4', 'text': 'I am working on a new version of my website this week.'},
    {'file': 'input1.mp4', 'text': 'And that's why I am so excited about this new project.'}
    }
'''

response = client.chat.completions.create(
    model="gpt-4o",
    response_format={"type": "json_object"},
    messages=[
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": transcription_strings}
    ]
)
print("GPT Response 1 ",
      response.choices[0].message.content)
gpt_response_1 = response.choices[0].message.content
edited_transcript_json = json.loads(gpt_response_1)
edited_script = edited_transcript_json['desired_transcription']
edited_transcription_sources = edited_transcript_json['transcription_sources']

print("Edited script: ", edited_script)
print("Edited transcription sources: ", edited_transcription_sources)


# second GPT prompt
system_prompt_2 = ''' You are an expert video editor who is given the transcriptions of extracts of video files and the start end time of various words in an original video clip and then returns a json object of which start and end times of the original video to combine to achieve the edited video. Please extract the start and end time for each given file from the passed in transcript, matching the words exactly. The end time must obviously come after the start time for each clip. For example an output could be:
    {
    desired_transcription: "Hey what's up it is Tuesday afternoon. I am working on a new version of my website this week. And that's why I am so excited about this new project.",
    transcription_times: [{'file': 'input1.mp4', 'start': 1.2345322, 'end': 4.238438},
    {'file': 'input2.mp4', 'start': 9.4723769, 'end': 14.36824864},
    {'file': 'input1.mp4', 'start': 27.3444331, 'end': 35.3961112}
    }
'''

user_prompt = 'Here is the original transcriptions: ' + \
    str(transcriptions) + \
    " and here is the desired edited transcription outputs: " + gpt_response_1

response_2 = client.chat.completions.create(
    model="gpt-4o",
    response_format={"type": "json_object"},
    messages=[
        {"role": "system", "content": system_prompt_2},
        {"role": "user", "content": user_prompt}
    ]
)

print("GPT Response 2 ",
      response_2.choices[0].message.content)
edited_times_json = json.loads(response_2.choices[0].message.content)
editing_instructions = edited_times_json['transcription_times']

# editing_instructions = []


# # find all transcription sources' time codes
# for clip in edited_transcription_sources:
#     video_filename = clip['file']
#     video_text = clip['text']
#     start_time = None
#     end_time = None
#     # Find the object with the video name "input2"
#     target_transcription = next(
#         (item for item in transcriptions if item['video'] == video_filename), None)
#     if target_transcription:
#         # Access the transcription object

#         transcript_word_array = target_transcription['transcription_object'].words
#         print("transcript_word_array: ", transcript_word_array)
#         input_words = video_text.replace(",", "").split()

#         # Helper function to find the sequence of words in the words array
#         def find_sequence(words, input_words):
#             i = 0  # Index for input_words
#             n = len(input_words)
#             for word_info in words:
#                 if word_info['word'].casefold() == input_words[i].casefold():
#                     if i == 0:
#                         start_time = word_info['start']
#                     if i == n - 1:
#                         end_time = word_info['end']
#                         return start_time, end_time
#                     i += 1
#                 else:
#                     i = 0  # Reset the index if sequence breaks
#             return None, None

#         start_time, end_time = find_sequence(
#             transcript_word_array, input_words)

#         if start_time is not None and end_time is not None:
#             print(f"Start time: {start_time}, End time: {end_time}")
#             editing_instructions.append(
#                 {"file": video_filename, "start": start_time, "end": end_time})
#         else:
#             print("The input sentence sequence was not found in the words array.")
#             editing_instructions.append(
#                 {'file': video_filename, 'start': start_time, 'end': end_time})

# print("editing_instructions: ", editing_instructions)

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
