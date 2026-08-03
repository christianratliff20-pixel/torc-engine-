import os
import json
import subprocess
from celery import Celery
import yt_dlp
from deepgram import DeepgramClient, PrerecordedOptions
from anthropic import Anthropic
from app.database import SessionLocal
from app.models import Project, Highlight, Clip
import uuid

celery_app = Celery("tasks", broker=os.getenv("REDIS_URL", "redis://localhost:6379/0"))
anthropic_client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY", "mock-key"))
deepgram = DeepgramClient(os.getenv("DEEPGRAM_API_KEY", "mock-key"))

def download_video(url: str, output_path: str):
    ydl_opts = {
        'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/mp4',
        'outtmpl': output_path,
        'quiet': True,
        'no_warnings': True,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])

def transcribe_audio_deepgram(audio_path: str):
    with open(audio_path, "rb") as audio:
        payload = {"buffer": audio}
        options = PrerecordedOptions(
            model="nova-2",
            smart_format=True,
            diarize=True,
            utterances=True,
        )
        response = deepgram.listen.rest.v("1").transcribe_file(payload, options)
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
    db = SessionLocal()
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        return
    
    video_path = f"/tmp/{project.id}.mp4"
    
    try:
        project.status = "fetching"
        db.commit()
        if url:
            download_video(url, video_path)

        project.status = "transcribing"
        db.commit()
        transcript_chunks = transcribe_audio_deepgram(video_path)

        with open(f"/tmp/{project.id}_transcript.json", "w") as f:
            json.dump(transcript_chunks, f)

        run_detection_pass_two(project_id, db_session=db, transcript_chunks=transcript_chunks)
        
    except Exception as e:
        project.status = "failed"
        project.error_message = str(e)
        db.commit()

@celery_app.task
def run_detection_pass_two(project_id: str, db_session=None, transcript_chunks=None):
    db = db_session or SessionLocal()
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        return
    
    project.status = "detecting"
    db.commit()
    
    if not transcript_chunks:
        try:
            with open(f"/tmp/{project.id}_transcript.json", "r") as f:
                transcript_chunks = json.load(f)
        except FileNotFoundError:
            project.status = "failed"
            project.error_message = "Transcript file lost. Please re-upload source."
            db.commit()
            return

    previous_highlights = db.query(Highlight).filter(Highlight.project_id == project.id).all()
    previous_ranges = [
        {"start": h.start_seconds, "end": h.end_seconds} for h in previous_highlights
    ]

    negative_constraint_prompt = ""
    if previous_ranges:
        negative_constraint_prompt = f"""
        NEGATIVE CONSTRAINTS (CRITICAL):
        The user has already generated clips covering the following timestamp ranges:
        {json.dumps(previous_ranges)}
        Do NOT repeat these exact timestamp ranges unless the user's specific prompt explicitly requests a deeper focus on that exact topic.
        """

    prompt = f"""
    You are an expert viral video editor.
    USER INSTRUCTIONS: '{project.instructions or "Detect top viral engaging moments"}'
    STYLE PRESET: {project.preset}
    TARGET CLIP COUNT: {project.clip_count}

    {negative_constraint_prompt}

    Review these transcript sentence chunks:
    {json.dumps(transcript_chunks)}

    Only return raw JSON as an array of clip objects:
    [
      {{
        "start": float,
        "end": float,
        "label": "string",
        "score": int,
        "subCuts": [
          {{ "start": float, "end": float, "text": "sentence text" }}
        ]
      }}
    ]
    Do NOT include markdown block formatting.
    """
    
    try:
        response = anthropic_client.messages.create(
            model="claude-3-5-sonnet-20240620",
            max_tokens=2500,
            messages=[{"role": "user", "content": prompt}]
        )
        
        raw_text = response.content[0].text.strip('```json').strip('```').strip()
        ai_clips = json.loads(raw_text)
        
        clip_limit = int(project.clip_count) if project.clip_count and project.clip_count.isdigit() else len(ai_clips)
        ai_clips = ai_clips[:clip_limit]
        
        for clip in ai_clips:
            new_hl = Highlight(
                id=f"hl-{uuid.uuid4().hex[:8]}",
                project_id=project.id,
                batch_id=project.redos_used + 1,
                start_seconds=clip['start'],
                end_seconds=clip['end'],
                score=clip['score'],
                label=clip['label'],
                is_manual=False,
                is_smart_clip=True,
                sub_cuts_json=json.dumps(clip.get('subCuts', []))
            )
            db.add(new_hl)
            
        project.status = "ready"
        if transcript_chunks:
            project.duration_seconds = transcript_chunks[-1]['end'] 
        db.commit()
        
    except Exception as e:
        project.status = "failed"
        project.error_message = f"AI Detection Pass Failed: {str(e)}"
        db.commit()

@celery_app.task
def render_final_clip(clip_id: str):
    db = SessionLocal()
    clip = db.query(Clip).filter(Clip.id == clip_id).first()
    if not clip:
        return
    
    highlight = db.query(Highlight).filter(Highlight.id == clip.highlight_id).first()
    if not highlight:
        clip.status = "failed"
        clip.error_message = "Highlight record missing."
        db.commit()
        return

    clip.status = "rendering"
    db.commit()
    
    input_file = f"/tmp/{highlight.project_id}.mp4"
    output_file = f"/tmp/final_{clip.id}.mp4"
    
    try:
        command = [
            "ffmpeg", "-y", "-i", input_file, 
            "-ss", str(highlight.start_seconds), 
            "-to", str(highlight.end_seconds), 
            "-c:v", "libx264", "-c:a", "aac", output_file
        ]
        subprocess.run(command, check=True)
        
        clip.status = "rendered"
        clip.output_path = output_file
        db.commit()
    except subprocess.CalledProcessError as e:
        clip.status = "failed"
        clip.error_message = f"FFmpeg processing failed: {str(e)}"
        db.commit()
