# LLM Video Editor
![thumb](https://github.com/mitch7w/ai-video-editor/assets/58911571/2da3031f-ddf8-4889-90d9-a23cd6c56a9a)

## Use an LLM to stitch together multiple videos and do the rough-cut of video editing for you.

It's rough, it sometimes still includes pauses and mistakes in the final video and it only works with video with dialogue in it but it can do a decent job and is a proof-of-concept that video editing with LLMs is possible.
Products like http://Gling.ai obviosuly show how powerful this workflow is and will only get better as the underlying models do too. This uses Claude 3.5 Sonnet as GPT-4o wasn't handling the cuts so nicely.

To use:
1. Download the code
2. Create a .env file with your OPENAI_API_KEY and ANTHROPIC_API_KEY set inside of it.
3. Run pip install -r requirements.txt
4. Place the input videos you want edited into the same folder as the code and enter the filenames in the video_files array at the top of the ai_video_editor_simple.py file.
5. Run and check out the ai_output.mp4 video when it's done.
