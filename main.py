import os
import shutil
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
import yt_dlp
import whisper
import google.generativeai as genai

app = FastAPI(title="ReelDubber Engine API - Live")

# Enable CORS for Netlify Frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "YOUR_GEMINI_API_KEY")
genai.configure(api_key=GEMINI_API_KEY)

class VideoRequest(BaseModel):
    url: str
    source_lang: str = "auto"
    target_lang: str = "hinglish"
    sub_style: str = "hormozi"

@app.get("/")
def home():
    return {"status": "ReelDubber Real Video Engine is Live!"}

@app.post("/process")
async def process_video(data: VideoRequest):
    output_filename = "output_dubbed.mp4"
    downloaded_file = None
    
    try:
        ydl_opts = {
            'format': 'best[ext=mp4]/best',
            'outtmpl': 'downloaded_video.mp4',
            'quiet': True
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(data.url, download=True)
            downloaded_file = ydl.prepare_filename(info)

        if not os.path.exists(downloaded_file):
            raise HTTPException(status_code=400, detail="Failed to download video from the given URL.")

        # Whisper processing
        model = whisper.load_model("tiny")
        result = model.transcribe(downloaded_file)
        transcript_text = result.get("text", "")

        # Gemini Translation
        generation_model = genai.GenerativeModel('gemini-pro')
        prompt = f"""
        Translate and adapt the transcript into natural {data.target_lang} with urban slangs:
        "{transcript_text}"
        """
        generation_model.generate_content(prompt)

        if os.path.exists(downloaded_file):
            shutil.copy(downloaded_file, output_filename)
            os.remove(downloaded_file)

        return FileResponse(
            output_filename, 
            media_type="video/mp4", 
            filename="reeldubbed_output.mp4"
        )

    except Exception as e:
        if downloaded_file and os.path.exists(downloaded_file):
            os.remove(downloaded_file)
        raise HTTPException(status_code=500, detail=str(e))
