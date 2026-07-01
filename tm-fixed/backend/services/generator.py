import asyncio
import logging

from sqlmodel import Session, select

from backend.database import engine
from backend.models import Job, Thumbnail
from backend.services.openai_service import generate_thumbnails
from backend.services.imagekit_service import upload_image

logger = logging.getLogger(__name__)

STYLES: dict[str, str] = {
    "bold_dramatic": (
        "Create a bold, dramatic YouTube thumbnail with high contrast, "
        "cinematic lighting, dark moody background, and powerful composition. "
        "The person's face should be prominent with a dramatic expression."
    ),
    "clean_minimal": (
        "Create a clean, minimal YouTube thumbnail with bright lighting, "
        "white/light background, modern professional aesthetic, plenty of "
        "whitespace, and sharp clean composition. The person should look "
        "approachable and professional."
    ),
    "vibrant_energetic": (
        "Create a vibrant, energetic YouTube thumbnail with colorful "
        "gradients, dynamic angles, eye-catching pop-art style colors, "
        "and energetic composition. The person should have an excited or "
        "engaging expression."
    ),
}

STYLE_ORDER = ["bold_dramatic", "clean_minimal", "vibrant_energetic"]


async def generate_single_thumbnail(
    thumbnail_id: str, prompt: str, headshot_url: str
) -> None:
    # 1. Mark as generating and grab style info — all within one session
    with Session(engine) as session:
        thumb = session.get(Thumbnail, thumbnail_id)
        if not thumb:
            logger.error(f"Thumbnail {thumbnail_id} not found in DB")
            return
        thumb.status = "generating"
        style_name = thumb.style_name
        job_id = thumb.job_id          # capture the FK value while session is open
        session.add(thumb)
        session.commit()

    style_prompt = STYLES.get(style_name, "")

    # 2. Call OpenAI (async, outside any DB session)
    try:
        image_bytes = await generate_thumbnails(prompt, style_prompt, headshot_url)

        # 3. Upload to ImageKit
        url = upload_image(
            file_bytes=image_bytes,
            file_name=f"{thumbnail_id}.png",
            folder=f"thumbnails/{job_id}/",
        )

        # 4. Persist success
        with Session(engine) as session:
            thumb = session.get(Thumbnail, thumbnail_id)
            thumb.imagekit_url = url
            thumb.status = "uploaded"
            session.add(thumb)
            session.commit()
            logger.info(f"Thumbnail {thumbnail_id} uploaded successfully → {url}")

    except Exception as exc:
        logger.error(f"Thumbnail {thumbnail_id} failed: {exc}")
        with Session(engine) as session:
            thumb = session.get(Thumbnail, thumbnail_id)
            thumb.status = "failed"
            thumb.error_message = str(exc)[:500]
            session.add(thumb)
            session.commit()


async def process_job(job_id: str) -> None:
    """Mark the job as processing, spin up one worker per thumbnail, then finalise."""
    # 1. Mark job processing and collect thumbnail IDs
    with Session(engine) as session:
        job = session.get(Job, job_id)
        if not job:
            logger.error(f"Job {job_id} not found")
            return
        job.status = "processing"
        prompt = job.prompt
        headshot_url = job.headshot_url
        session.add(job)
        session.commit()

        thumbnails = session.exec(
            select(Thumbnail).where(Thumbnail.job_id == job_id)
        ).all()
        thumbnail_ids = [t.id for t in thumbnails]

    # 2. Run all thumbnail workers concurrently
    tasks = [
        generate_single_thumbnail(tid, prompt, headshot_url)
        for tid in thumbnail_ids
    ]
    await asyncio.gather(*tasks, return_exceptions=True)

    # 3. Mark job as completed or failed
    with Session(engine) as session:
        thumbnails = session.exec(
            select(Thumbnail).where(Thumbnail.job_id == job_id)
        ).all()
        all_failed = all(t.status in ("failed",) for t in thumbnails)

        job = session.get(Job, job_id)
        job.status = "failed" if all_failed else "completed"
        session.add(job)
        session.commit()
        logger.info(f"Job {job_id} finished with status={job.status}")
