from datetime import datetime, timedelta
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from app.core.database import get_db
from feature.models.video import CompilationStatus
from feature.repository.video_repository import VideoRepository


async def run_deadline_sweep():
    with get_db() as db:
        rooms = VideoRepository.get_rooms_past_deadline_without_compilation(db, datetime.utcnow())
        for room in rooms:
            from feature.services.video_service import VideoService
            await VideoService.start_stitch(db, room.id)


async def reset_stale_jobs():
    with get_db() as db:
        cutoff = datetime.utcnow() - timedelta(minutes=10)
        stale = VideoRepository.get_stale_processing_jobs(db, cutoff)
        for comp in stale:
            comp.status = CompilationStatus.PENDING
        if stale:
            db.commit()


def start_scheduler():
    scheduler = AsyncIOScheduler()
    scheduler.add_job(run_deadline_sweep, IntervalTrigger(seconds=60), id="deadline_sweep")
    scheduler.add_job(reset_stale_jobs, IntervalTrigger(seconds=300), id="stale_job_reset")
    scheduler.start()
    return scheduler
