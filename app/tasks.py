from app.worker import celery_app
from app.database import SessionLocal
from app import models
from app.pipeline import extract, prefilter, transcription, detection


@celery_app.task(bind=True, max_retries=2)
def run_extraction(self, project_id: str):
    db = SessionLocal()
    try:
        project = db.query(models.Project).get(project_id)
        try:
            file_path = extract.extract(project.source_url, project.source_type.value)
        except Exception:
            try:
                file_path = extract.extract(project.source_url, project.source_type.value, audio_only=True)
            except Exception as e:
                project.status = models.ProjectStatus.failed
                db.commit()
                raise self.retry(exc=e, countdown=30)

        project.file_path = file_path
        project.status = models.ProjectStatus.transcribing
        db.commit()
        run_transcription.delay(project_id)
    finally:
        db.close()


@celery_app.task(bind=True, max_retries=2)
def run_transcription(self, project_id: str):
    db = SessionLocal()
    try:
        project = db.query(models.Project).get(project_id)

        keep_spans = prefilter.prefilter(project.file_path)
        words = transcription.transcribe(project.file_path)

        project.transcript = " ".join(w.text for w in words)
        project.status = models.ProjectStatus.detecting
        db.commit()
        run_detection.delay(project_id)
    except Exception as e:
        db.rollback()
        raise self.retry(exc=e, countdown=30)
    finally:
        db.close()


@celery_app.task(bind=True, max_retries=1)
def run_detection(self, project_id: str):
    db = SessionLocal()
    try:
        project = db.query(models.Project).get(project_id)

        words = []
        candidates = detection.detect_v0_transcript_only(words, user_instruction=project.user_instruction)

        for c in candidates:
            db.add(models.Highlight(
                project_id=project.id,
                start_seconds=c.start_seconds,
                end_seconds=c.end_seconds,
                label=c.label,
                score=c.score,
                matches_instruction=c.matches_instruction,
                instruction_reasoning=c.instruction_reasoning,
            ))

        project.status = models.ProjectStatus.ready
        db.commit()
    except Exception as e:
        db.rollback()
        project = db.query(models.Project).get(project_id)
        project.status = models.ProjectStatus.failed
        db.commit()
        raise
    finally:
        db.close()
