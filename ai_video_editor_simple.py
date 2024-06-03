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
    simplified_words = []
    for each in transcriptions:
        words_array = each['transcription_object'].words
        for word in words_array:
            simplified_words.append({word['word'], word['start'], word['end']})

print("simplified_words: ", simplified_words)

# now actually perform editing process with GPT-4o

system_prompt = ''' You are an expert video editor who is given an array of words spoken in a video and their start and end times. You return a json object of which words to stitch together in what order. Please combine videos by extracting the exact words you want in the edited version from the given array. Do not add words - only use those given to you alongside their start and end times. Edit out repeated sentences and false starts so the video is concise and follows a natural script. If the speaker says the same sentence twice please rather just extract the second one as it is probably more correct. For example the input: "Hey, what's up? So it is Tuesday afternoon, and I've had a pretty productive day so far. I've just been working on my AI video generator, which is quite cool. It's doing, hey, what's up? So I've been working on my AI video generator this afternoon. It's been going pretty well. And I've got the transcription working with Whisper in the background. I've got the cutting up and stitching together the final output done with FFmeg. And now I'm just busy working on actually like getting the editing and the cutting of the files together nicely with GBT so that it can basically edit videos for you. Because I actually don't enjoy the video editing process. I find it very laborious and time consuming and not that interesting when I could be doing more cool things. And then I could actually, so like the intention behind the tool is actually for me to sit down, set up the whole tool so that I can record 10 minutes of footage and then just throw it into this tool and have it spit out a half decently edited file." will yield the following output:
    {
    desired_transcription: "hey, what's up? So I've been working on my AI video generator this afternoon. It's been going pretty well. And I've got the transcription working with Whisper in the background. I've got the cutting up and stitching together the final output done with FFmeg. And now I'm just busy working on actually like getting the editing and the cutting of the files together nicely with GBT so that it can basically edit videos for you. Because I actually don't enjoy the video editing process. I find it very laborious and time consuming and not that interesting when I could be doing more cool things. so like the intention behind the tool is actually for me to sit down, set up the whole tool so that I can record 10 minutes of footage and then just throw it into this tool and have it spit out a half decently edited file.",
    transcription_sources: [{'file': 'update.mp4', 'start': 9.2345322, 'end': 14.238438},
    {'file': 'update.mp4', 'start': 20.4723769, 'end': 26.36824864},
    {'file': 'update.mp4', 'start': 33.3444331, 'end': 48.3961112}
    }

    Note how repeated sentences have been cut out and mistakes or non-cohesive thoughts edited out.
'''

response = client.chat.completions.create(
    model="gpt-4o",
    response_format={"type": "json_object"},
    messages=[
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": str(simplified_words)}
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

# TODO problem is with GPT call. Change prompt and give one shot example.
# TODO test just moving system prompt to user prompt but i doubt it and this is more finegraned anyway
