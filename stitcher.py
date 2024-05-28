import ffmpeg

video_files = [
    {'file': 'vai_1.mp4', 'start': 2.2, 'end': 10},
    {'file': 'vai_2.mp4', 'start': 5, 'end': 15},
    {'file': 'vai_3.mp4', 'start': 2, 'end': 8},
]

# Create a list of ffmpeg inputs with specified start and end times
inputs = [ffmpeg.input(video['file'], ss=video['start'],
                       to=video['end']) for video in video_files]

# Create a list of tuples, each containing the video and audio streams of a file
stream_pairs = [(input.video, input.audio) for input in inputs]

# Concatenate the video clips
if stream_pairs:
    concat = ffmpeg.concat(
        *[item for sublist in stream_pairs for item in sublist], v=1, a=1).node
    output = ffmpeg.output(concat[0], concat[1], 'output.mp4')
    output.run()

print("Video concatenation complete. Output saved as 'output.mp4'.")
