# main.py
# Beyond Earth — Auto Short Maker & YouTube Uploader (GitHub Actions)
import os
import random
import requests
import tempfile
from gtts import gTTS
from moviepy.editor import VideoFileClip, concatenate_videoclips, AudioFileClip, TextClip, CompositeVideoClip
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
import time

# ---------- CONFIG (from env/secrets) ----------
PEXELS_API = os.environ.get("PEXELS_API", "")
YT_CLIENT_ID = os.environ.get("YOUTUBE_CLIENT_ID", "")
YT_CLIENT_SECRET = os.environ.get("YOUTUBE_CLIENT_SECRET", "")
YT_REFRESH_TOKEN = os.environ.get("YOUTUBE_REFRESH_TOKEN", "")
UPLOAD_TITLE_PREFIX = os.environ.get("UPLOAD_TITLE_PREFIX", "Beyond Earth — ")

# ---------- Simple script pool (you can expand) ----------
SCRIPTS = [
    ("What is a black hole?", "Black holes warp time and space. If you fell in, you would be stretched and frozen from the outside view."),
    ("Time dilation explained", "Move very fast and time for you slows. Einstein showed speed and time are linked."),
    ("Exoplanets and life", "A planet in the habitable zone might host life — but life could prefer strange oceans and skies."),
    ("Why stars twinkle", "Twinkling is caused by Earth's atmosphere bending starlight. In space, stars do not twinkle.")
]

def pick_script():
    title_hint, text = random.choice(SCRIPTS)
    return title_hint, text

# ---------- Utilities ----------
def download_pexels_clip(query="space galaxy", max_duration=45):
    headers = {"Authorization": PEXELS_API}
    params = {"query": query, "per_page": 5}
    r = requests.get("https://api.pexels.com/videos/search", headers=headers, params=params, timeout=30)
    r.raise_for_status()
    data = r.json()
    if not data.get("videos"):
        raise RuntimeError("No videos from Pexels for query: " + query)
    # pick first suitable file (mp4)
    for vid in data["videos"]:
        files = vid.get("video_files", [])
        for f in files:
            if f.get("width") and f.get("link") and "mp4" in f.get("file_type","mp4"):
                return f["link"]
    raise RuntimeError("No mp4 video file found in Pexels response")

def generate_tts(text, out_path):
    tts = gTTS(text=text, lang="en")
    tts.save(out_path)

def make_video(clip_url, tts_path, out_path, title_text):
    # download clip
    tmp_clip = tempfile.NamedTemporaryFile(suffix=".mp4", delete=False).name
    with requests.get(clip_url, stream=True, timeout=60) as r:
        r.raise_for_status()
        with open(tmp_clip, "wb") as f:
            for chunk in r.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
    # load video and audio
    video = VideoFileClip(tmp_clip)
    audio = AudioFileClip(tts_path)
    # trim or loop video to match audio length (audio length in seconds)
    dur = audio.duration
    if video.duration >= dur:
        clip = video.subclip(0, dur)
    else:
        # loop the clip until it covers audio
        loops = int(dur // video.duration) + 1
        clips = [video] * loops
        clip = concatenate_videoclips(clips).subclip(0, dur)
    # add a short intro text clip
    intro = TextClip(title_text, fontsize=70, color='white', font='Arial-Bold').set_duration(1.5).set_pos('center')
    intro = intro.on_color(size=(clip.w, clip.h), color=(0,0,0), col_opacity=0.6)
    final = concatenate_videoclips([intro, clip])
    final = final.set_audio(audio)
    # add subtitle as overlay (simple)
    subtitle = TextClip(text=title_text, fontsize=40, color='white', stroke_color='black', stroke_width=3, method='caption', size=(int(clip.w*0.9), None)).set_duration(final.duration).set_pos(('center', int(clip.h*0.75)))
    composite = CompositeVideoClip([final, subtitle])
    composite.write_videofile(out_path, fps=24, codec="libx264", audio_codec="aac", threads=2, logger=None)
    # cleanup tmp
    try:
        os.remove(tmp_clip)
    except:
        pass

# ---------- YouTube upload ----------
def get_youtube_service():
    creds = Credentials(
        None,
        refresh_token=YT_REFRESH_TOKEN,
        token=None,
        client_id=YT_CLIENT_ID,
        client_secret=YT_CLIENT_SECRET,
        scopes=["https://www.googleapis.com/auth/youtube.upload"]
    )
    creds.refresh(requests.Request())
    service = build("youtube", "v3", credentials=creds)
    return service

def upload_video_to_youtube(video_file, title, description, tags=None, privacy="public"):
    service = get_youtube_service()
    body = {
        "snippet": {"title": title, "description": description, "tags": tags or [], "categoryId": "28"},
        "status": {"privacyStatus": privacy}
    }
    media = MediaFileUpload(video_file, chunksize=-1, resumable=True, mimetype="video/*")
    req = service.videos().insert(part="snippet,status", body=body, media_body=media)
    resp = None
    while resp is None:
        status, resp = req.next_chunk()
    return resp

# ---------- Main flow ----------
def main():
    print("Starting job")
    title_hint, script_text = pick_script()
    full_title = UPLOAD_TITLE_PREFIX + title_hint
    # tts
    tts_file = "voice.mp3"
    generate_tts(script_text, tts_file)
    # pexels clip
    clip_url = download_pexels_clip(query="cinematic space galaxy")
    # create video
    out_file = f"final_{int(time.time())}.mp4"
    make_video(clip_url, tts_file, out_file, title_hint)
    print("Video created:", out_file)
    # YouTube description
    description = f"{script_text}\n\nSubscribe to Beyond Earth for daily cosmic shorts.\n#BeyondEarth #Space #Science"
    # upload
    if YT_CLIENT_ID and YT_CLIENT_SECRET and YT_REFRESH_TOKEN:
        print("Uploading to YouTube...")
        resp = upload_video_to_youtube(out_file, full_title, description, tags=["Space","Science","Shorts"])
        print("Upload response:", resp.get("id"))
    else:
        print("YouTube keys not provided — skipping upload. Video is saved.")
    # done
    print("Job finished")

if __name__ == "__main__":
    main()
