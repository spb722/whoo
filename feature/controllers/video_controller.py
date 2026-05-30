import os
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Header, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.config import settings
from app.core.database import get_db_dependency
from app.core.error_handler import create_success_response
from app.models.user import User
from feature.models.video import CompilationStatus
from feature.repository.video_repository import VideoRepository
from feature.schemas.video_schema import (
    CompilationConfigRequest,
    CompilationStatusResponse,
    WorkerResultRequest,
)
from feature.services.video_service import VideoService
from feature.models.room import Room

router = APIRouter(prefix="/rooms", tags=["videos"])
internal_router = APIRouter(prefix="/internal", tags=["internal"])


def _verify_worker_key(x_worker_key: str = Header(...)):
    if not settings.WORKER_API_KEY or x_worker_key != settings.WORKER_API_KEY:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid worker key")


def _playback_url(storage_key: str) -> str:
    return f"{settings.MEDIA_BASE_URL}/{storage_key}"


# ─── Frontend endpoints ────────────────────────────────────────────────────────

@router.post("/{room_id}/videos")
async def upload_video(
    room_id: str,
    file: UploadFile = File(...),
    duration: Optional[float] = Form(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db_dependency),
):
    success, message, video = await VideoService.upload_video(
        db, room_id, current_user.id, file, duration
    )
    if not success:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=message)

    data = {
        "video_id": video.id,
        "room_id": video.room_id,
        "user_id": video.user_id,
        "playback_url": _playback_url(video.storage_key),
        "duration_seconds": video.duration_seconds,
        "file_size_bytes": video.file_size_bytes,
        "status": video.status.value,
        "created_at": video.created_at,
    }
    return create_success_response(message=message, data=data)


@router.get("/{room_id}/videos")
async def list_videos(
    room_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db_dependency),
):
    room = db.query(Room).filter(Room.id == room_id).first()
    if not room:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Room not found")

    videos = VideoRepository.get_videos_for_room(db, room_id)
    data = [
        {
            "video_id": v.id,
            "room_id": v.room_id,
            "user_id": v.user_id,
            "playback_url": _playback_url(v.storage_key),
            "duration_seconds": v.duration_seconds,
            "file_size_bytes": v.file_size_bytes,
            "status": v.status.value,
            "created_at": v.created_at,
        }
        for v in videos
    ]
    return create_success_response(message="Videos retrieved", data=data)


@router.get("/{room_id}/videos/me")
async def get_my_video(
    room_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db_dependency),
):
    video = VideoRepository.get_video_for_user(db, room_id, current_user.id)
    if not video:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No video found for this room")

    data = {
        "video_id": video.id,
        "room_id": video.room_id,
        "user_id": video.user_id,
        "playback_url": _playback_url(video.storage_key),
        "duration_seconds": video.duration_seconds,
        "file_size_bytes": video.file_size_bytes,
        "status": video.status.value,
        "created_at": video.created_at,
    }
    return create_success_response(message="Video retrieved", data=data)


@router.delete("/{room_id}/videos/{video_id}")
async def delete_video(
    room_id: str,
    video_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db_dependency),
):
    video = VideoRepository.get_video_by_id(db, video_id)
    if not video or video.room_id != room_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Video not found")
    if video.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot delete another user's video")

    abs_path = os.path.join(settings.MEDIA_ROOT, video.storage_key)
    if os.path.exists(abs_path):
        os.remove(abs_path)

    VideoRepository.delete_video(db, video)
    return create_success_response(message="Video deleted", data=None)


@router.post("/{room_id}/compilation")
async def save_compilation_config(
    room_id: str,
    request: CompilationConfigRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db_dependency),
):
    room = db.query(Room).filter(Room.id == room_id).first()
    if not room:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Room not found")
    if room.owner_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only the room owner can set compilation config")

    meta = room.room_metadata or {}
    meta["template_id"] = request.template_id
    if request.config is not None:
        meta["compilation_config"] = request.config
    room.room_metadata = meta
    db.commit()

    return create_success_response(message="Compilation config saved", data={"template_id": request.template_id})


@router.get("/{room_id}/compilation")
async def get_compilation_status(
    room_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db_dependency),
):
    room = db.query(Room).filter(Room.id == room_id).first()
    if not room:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Room not found")

    comp = VideoRepository.get_compilation_for_room(db, room_id)
    if not comp:
        return create_success_response(message="No compilation yet", data=None)

    video_url = None
    if comp.status == CompilationStatus.COMPLETED and comp.storage_key:
        video_url = _playback_url(comp.storage_key)

    data = {
        "compilation_id": comp.id,
        "room_id": comp.room_id,
        "status": comp.status.value,
        "video_count": comp.video_count,
        "video_url": video_url,
        "error_message": comp.error_message,
        "created_at": comp.created_at,
        "completed_at": comp.completed_at,
    }
    return create_success_response(message="Compilation status retrieved", data=data)


# ─── Internal worker endpoints ─────────────────────────────────────────────────

@internal_router.post("/compilations/claim")
async def claim_compilation(
    db: Session = Depends(get_db_dependency),
    _: None = Depends(_verify_worker_key),
):
    success, message, payload = VideoService.claim_job(db)
    if not success or payload is None:
        from fastapi.responses import Response
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    return create_success_response(message=message, data=payload)


@internal_router.post("/compilations/{compilation_id}/result")
async def report_compilation_result(
    compilation_id: str,
    request: WorkerResultRequest,
    db: Session = Depends(get_db_dependency),
    _: None = Depends(_verify_worker_key),
):
    success, message, _ = VideoService.record_result(
        db,
        compilation_id,
        status=request.status,
        storage_key=request.storage_key,
        error_message=request.error_message,
        video_count=request.video_count,
    )
    if not success:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=message)
    return create_success_response(message=message, data=None)
