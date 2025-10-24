# Beyond Earth Auto YouTube Shorts Creator (Demo Version)
# Free Auto Reel Maker using gTTS + Pexels (no paid API needed)

import os
import random
import requests
from gtts import gTTS
from moviepy.editor import VideoFileClip, concatenate_videoclips, TextClip, CompositeVideoClip

# --- CONFIG --- #
PEXELS_API = "YOUR_PEXELS_API_KEY"  # Replace with free API key from pexels.com/api
os.makedirs("videos", exist_ok=True)

# --- SCRIPT --- #
scripts = [
    "The universe is vast, mysterious, and endlessly fascinating.",
    "Every star in the night sky has its own story to tell.",
    "What lies beyond our galaxy? The search continues..."
]
text = random.choice(scripts)

# --- VOICE --- #
tts = gTTS(text=text, lang='en')
tts.save("voice.mp3")

# --- VIDEO --- #
headers = {"Authorization": PEXELS_API}
query = "space stars galaxy"
response = requests.get(f"https://api.pexels.com/videos/search?query={query}&per_page=1", headers=headers)
video_url = response.json()['videos'][0]['video_files'][0]['link']

with open("background.mp4", "wb") as f:
    f.write(requests.get(video_url).content)

clip = VideoFileClip("background.mp4").subclip(0, 10)
txt = TextClip("Beyond Earth 🌌", fontsize=60, color='white', font="Arial-Bold").set_pos("center").set_duration(3)
final = concatenate_videoclips([txt, clip])
final.write_videofile("videos/final_video.mp4", codec="libx264", fps=24)

print("🎬 Auto video created successfully!")
