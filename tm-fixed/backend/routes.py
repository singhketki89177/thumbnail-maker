import asyncio
import json
import logging

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlmodel import Session, select

from backend.database import get_session, engine
from backend.models import Job, Thumbnail
from backend.services.generator import process_job, STYLE_ORDER
from backend.services.imagekit_service import get_variants, upload_image

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api")


# ── Request / Response schemas ─────────────────────────────────────────────


class JobCreateRequest(BaseModel):
    prompt: str
    num_thumbnails: int
    headshot_url: str


class CreateJobResponse(BaseModel):
    job_id: str


class ThumbnailResponse(BaseModel):
    id: str
    style_name: str
    imagekit_url: str | None = None
    status: str
    error_message: str | None = None
    variants: dict | None = None


class JobResponse(BaseModel):
    id: str          # str UUID — matches models.py
    prompt: str
    num_thumbnails: int
    headshot_url: str
    status: str
    thumbnails: list[ThumbnailResponse] = []


# ── Endpoints ──────────────────────────────────────────────────────────────


@router.post("/upload-headshot")
async def upload_headshot(file: UploadFile = File(...)):
    contents = await file.read()
    url = upload_image(
        file_bytes=contents,
        file_name=file.filename or "headshot.jpg",
        folder="/headshots",
        content_type=file.content_type or "image/jpeg",
    )
    return {"url": url}


@router.post("/jobs", response_model=CreateJobResponse)
async def create_job(
    request: JobCreateRequest,
    session: Session = Depends(get_session),
):
    if request.num_thumbnails < 1 or request.num_thumbnails > 3:
        raise HTTPException(
            status_code=400, detail="num_thumbnails must be between 1 and 3"
        )

    job = Job(
        prompt=request.prompt,
        num_thumbnails=request.num_thumbnails,
        headshot_url=request.headshot_url,
        status="pending",
    )
    session.add(job)
    session.commit()
    session.refresh(job)  # ensure job.id is populated before use

    styles = STYLE_ORDER[: request.num_thumbnails]
    for style in styles:
        thumb = Thumbnail(job_id=job.id, style_name=style)
        session.add(thumb)
    session.commit()

    # Fire-and-forget: generate thumbnails in background
    asyncio.create_task(process_job(job.id))

    return CreateJobResponse(job_id=job.id)


@router.get("/jobs/{job_id}", response_model=JobResponse)
def get_job(job_id: str, session: Session = Depends(get_session)):
    job = session.get(Job, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    thumbnails = session.exec(
        select(Thumbnail).where(Thumbnail.job_id == job_id)
    ).all()

    thumb_response: list[ThumbnailResponse] = [
        ThumbnailResponse(
            id=t.id,
            style_name=t.style_name,
            imagekit_url=t.imagekit_url,
            status=t.status,
            error_message=t.error_message,
            variants=get_variants(t.imagekit_url) if t.imagekit_url else None,
        )
        for t in thumbnails
    ]

    return JobResponse(
        id=job.id,
        prompt=job.prompt,
        num_thumbnails=job.num_thumbnails,
        headshot_url=job.headshot_url,
        status=job.status,
        thumbnails=thumb_response,
    )


@router.get("/jobs/{job_id}/stream")
async def stream_job(job_id: str):
    """Server-Sent Events endpoint: streams thumbnail results as they finish."""

    async def event_generator():
        sent_thumbnails: set[str] = set()

        while True:
            with Session(engine) as session:
                job = session.get(Job, job_id)
                if not job:
                    yield (
                        f"event:error\n"
                        f"data:{json.dumps({'error': 'Job not found'})}\n\n"
                    )
                    return

                thumbnails = session.exec(
                    select(Thumbnail).where(Thumbnail.job_id == job_id)
                ).all()

                all_done = True
                for t in thumbnails:
                    if t.id in sent_thumbnails:
                        continue

                    if t.status == "uploaded":
                        data = json.dumps(
                            {
                                "thumbnail_id": t.id,
                                "style_name": t.style_name,
                                "imagekit_url": t.imagekit_url,
                                "variants": get_variants(t.imagekit_url),
                            }
                        )
                        yield f"event:thumbnail ready\ndata:{data}\n\n"
                        sent_thumbnails.add(t.id)

                    elif t.status == "failed":
                        data = json.dumps(
                            {
                                "thumbnail_id": t.id,
                                "style_name": t.style_name,
                                "error_message": t.error_message,
                            }
                        )
                        yield f"event:thumbnail ready\ndata:{data}\n\n"
                        sent_thumbnails.add(t.id)

                    else:
                        # Still pending or generating
                        all_done = False

                if all_done and len(sent_thumbnails) >= len(thumbnails):
                    done = json.dumps({"job_id": job_id, "status": job.status})
                    yield f"event:job complete\ndata:{done}\n\n"
                    return

            await asyncio.sleep(1.5)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
