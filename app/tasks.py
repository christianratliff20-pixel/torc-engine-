import os
import json
import subprocess
from celery import Celery
import yt_dlp
from deepgram import DeepgramClient, PrerecordedOptions
from anthropic import Anthropic
from .database import SessionLocal
from .models import Project, Highlight, Clip
import uuid

# Initialize clients
celery_app = Celery("tasks", broker=os.getenv("REDIS_URL", "redis://localhost:6379/0"))
anthropic_client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
deepgram = DeepgramClient(os.getenv("DEEPGRAM_API_KEY"))

def download_video(url: str, output_path: str):
    """Uses yt-dlp to download the best mp4 format."""
    ydl_opts = {
        'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/mp4',
        'outtmpl': output_path,
        'quiet': True,
        'no_warnings': True,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])

def transcribe_audio_deepgram(audio_path: str):
    """Sends the downloaded video to Deepgram for fast transcription + diarization."""
    with open(audio_path, "rb") as audio:
        payload = {"buffer": audio}
        options = PrerecordedOptions(
            model="nova-2",
            smart_format=True,
            diarize=True, # Speaker detection
            utterances=True, # Chunks text into sentences automatically
        )
        response = deepgram.listen.rest.v("1").transcribe_file(payload, options)
        
        # Extract the structured sentences/utterances
        utterances = response.results.utterances
        transcript_chunks = []
        for u in utterances:
            transcript_chunks.append({
                "start": u.start,
                "end": u.end,
                "speaker": u.speaker,
                "text": u.transcript
            })
        return transcript_chunks

@celery_app.task
def process_video_pipeline(project_id: str, url: str = None):
    """The Full Working Pipeline: Download -> Transcribe -> Detect"""
    db = SessionLocal()
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project: return
    
    video_path = f"/tmp/{project.id}.mp4"
    
    try:
        # 1. INGESTION (Download the video)
        project.status = "fetching"
        db.commit()
        if url:
            download_video(url, video_path)
        else:
            # If it was a file upload, it should already be saved to video_path by the router
            pass

        # 2. TRANSCRIPTION (Deepgram)
        project.status = "transcribing"
        db.commit()
        transcript_chunks = transcribe_audio_deepgram(video_path)

        # Save transcript to disk/S3 so we can use it for Redos later
        with open(f"/tmp/{project.id}_transcript.json", "w") as f:
            json.dump(transcript_chunks, f)

        # 3. DETECTION (Claude Two-Pass)
        run_detection_pass_two(project_id, db_session=db, transcript_chunks=transcript_chunks)
        
    except Exception as e:
        project.status = "failed"
        project.error_message = str(e)
        db.commit()

@celery_app.task
def run_detection_pass_two(project_id: str, db_session=None, transcript_chunks=None):
    """Runs the Anthropic Steerable AI Check"""
    db = db_session or SessionLocal()
    project = db.query(Project).filter(Project.id == project_id).first()
    
    project.status = "detecting"
    db.commit()
    
    if not transcript_chunks:
        try:
            with open(f"/tmp/{project.id}_transcript.json", "r") as f:
                transcript_chunks = json.load(f)
        except FileNotFoundError:
            project.status = "failed"
            project.error_message = "Transcript lost. Please re-upload."
            db.commit()
            return
    
    prompt = f"""
    You are an expert video editor. The user asked for: '{project.instructions or "Find highly engaging highlights"}'.
    Style Preset: {project.preset}.
    Review these transcript chunks. Return clips that match the user's instructions.
    Only return raw JSON. No markdown formatting. Format as an array of objects: [{{ "start": float, "end": float, "label": "string", "score": int }}].
    Transcript: {json.dumps(transcript_chunks)}
    """
    
    try:
        response = anthropic_client.messages.create(
            model="claude-3-5-sonnet-20240620",
            max_tokens=1500,
            messages=[{"role": "user", "content": prompt}]
        )
        
        # Parse the JSON response
        ai_clips = json.loads(response.content[0].text.strip('```json').strip('```'))
        
        # Apply target clip count limit if the user selected one
        clip_limit = int(project.clip_count) if project.clip_count and project.clip_count.isdigit() else len(ai_clips)
        ai_clips = ai_clips[:clip_limit]
        
        for clip in ai_clips:
            new_hl = Highlight(
                id=f"hl-{uuid.uuid4().hex[:8]}",
                project_id=project.id,
                start_seconds=clip['start'],
                end_seconds=clip['end'],
                score=clip['score'],
                label=clip['label'],
                matches_instruction=True
            )
            db.add(new_hl)
            
        project.status = "ready"
        # We need the video duration for the timeline slider to work correctly
        if transcript_chunks:
            project.duration_seconds = transcript_chunks[-1]['end'] 
        db.commit()
        
    except Exception as e:
        project.status = "failed"
        project.error_message = f"AI Detection Failed: {str(e)}"
        db.commit()

@celery_app.task
def render_final_clip(clip_id: str):
    """Cuts the final video using FFmpeg based on the user's adjusted timeline boundaries."""
    db = SessionLocal()
    clip = db.query(Clip).filter(Clip.id == clip_id).first()
    if not clip: return
    
    highlight = db.query(Highlight).filter(Highlight.id == clip.highlight_id).first()
    
    clip.status = "rendering"
    db.commit()
    
    input_file = f"/tmp/{highlight.project_id}.mp4"
    output_file = f"/tmp/final_{clip.id}.mp4"
    
    try:
        # The actual command that cuts the video based on the AI's timestamps
        command = [
            "ffmpeg", "-y", "-i", input_file, 
            "-ss", str(highlight.start_seconds), 
            "-to", str(highlight.end_seconds), 
            "-c:v", "libx264", "-c:a", "aac", output_file
        ]
        subprocess.run(command, check=True)
        
        clip.status = "rendered"
        clip.output_path = output_file # Connect to S3/R2 upload here later
        db.commit()
    except subprocess.CalledProcessError as e:
        clip.status = "failed"
        clip.error_message = f"FFmpeg processing failed: {str(e)}"
        db.commit()
