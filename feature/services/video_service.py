import os
import json
from typing import Tuple, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from fastapi import UploadFile

from app.core.config import settings
from feature.models.video import RoomVideo, RoomCompilation, VideoStatus, CompilationStatus
from feature.models.room import Room
from feature.repository.video_repository import VideoRepository
from feature.utils.storage import raw_path, final_path, storage_key_for_raw, storage_key_for_final

CHUNK_SIZE = 1024 * 1024  # 1 MB


class VideoService:

    @staticmethod
    async def upload_video(
        db: Session,
        room_id: str,
        user_id: int,
        file: UploadFile,
        duration: Optional[float],
    ) -> Tuple[bool, str, Optional[RoomVideo]]:
        try:
            room = db.query(Room).filter(Room.id == room_id).first()
            if not room:
                return False, "Room not found", None

            participant = VideoRepository.get_approved_participant(db, room_id, user_id)
            if not participant:
                return False, "You are not an approved participant of this room", None

            import uuid
            video_id = str(uuid.uuid4())
            abs_path = raw_path(room_id, video_id)

            bytes_written = 0
            try:
                with open(abs_path, "wb") as f:
                    while True:
                        chunk = await file.read(CHUNK_SIZE)
                        if not chunk:
                            break
                        bytes_written += len(chunk)
                        if bytes_written > settings.UPLOAD_MAX_BYTES:
                            f.close()
                            os.remove(abs_path)
                            return False, f"File exceeds maximum allowed size of {settings.UPLOAD_MAX_BYTES} bytes", None
                        f.write(chunk)
            except Exception as e:
                if os.path.exists(abs_path):
                    os.remove(abs_path)
                return False, f"Failed to save file: {str(e)}", None

            existing = VideoRepository.get_video_for_user(db, room_id, user_id)
            if existing:
                old_abs = os.path.join(settings.MEDIA_ROOT, existing.storage_key)
                if os.path.exists(old_abs):
                    os.remove(old_abs)
                existing.storage_key = storage_key_for_raw(room_id, video_id)
                existing.status = VideoStatus.UPLOADED
                existing.duration_seconds = duration
                existing.file_size_bytes = bytes_written
                db.commit()
                db.refresh(existing)
                video = existing
            else:
                video = RoomVideo(
                    id=video_id,
                    room_id=room_id,
                    user_id=user_id,
                    storage_key=storage_key_for_raw(room_id, video_id),
                    status=VideoStatus.UPLOADED,
                    duration_seconds=duration,
                    file_size_bytes=bytes_written,
                )
                VideoRepository.save_video(db, video)

            uploaded_count = VideoRepository.count_uploaded_clips(db, room_id)
            if room.expected_uploader_count and uploaded_count >= room.expected_uploader_count:
                await VideoService.start_stitch(db, room_id, requested_by=user_id)

            return True, "Video uploaded successfully", video

        except Exception as e:
            db.rollback()
            return False, f"Upload failed: {str(e)}", None

    @staticmethod
    async def start_stitch(
        db: Session,
        room_id: str,
        requested_by: Optional[int] = None,
    ) -> Tuple[bool, str, Optional[RoomCompilation]]:
        room = db.query(Room).filter(Room.id == room_id).first()
        if not room:
            return False, "Room not found", None

        clip_count = VideoRepository.count_uploaded_clips(db, room_id)
        if clip_count == 0:
            return False, "No clips to stitch", None

        meta = room.room_metadata or {}
        template_id = meta.get("template_id", "default")
        config_str = json.dumps(meta.get("compilation_config")) if meta.get("compilation_config") else None

        try:
            comp = RoomCompilation(
                room_id=room_id,
                template_id=template_id,
                config=config_str,
                status=CompilationStatus.PENDING,
                video_count=clip_count,
                requested_by=requested_by,
            )
            db.add(comp)
            db.commit()
            db.refresh(comp)
            return True, "Queued for stitching", comp
        except IntegrityError:
            db.rollback()
            return True, "Already queued", None

    @staticmethod
    def claim_job(db: Session) -> Tuple[bool, str, Optional[dict]]:
        try:
            comp = VideoRepository.claim_next_pending_job(db)
            if not comp:
                return False, "No pending jobs", None

            room = db.query(Room).filter(Room.id == comp.room_id).first()
            clips_with_users = VideoRepository.get_clips_with_users(db, comp.room_id)

            clip_list = []
            for idx, (video, user) in enumerate(clips_with_users, start=1):
                user_name = f"{user.first_name or ''} {user.last_name or ''}".strip() or f"User {user.id}"
                clip_list.append({
                    "video_id": video.id,
                    "user_name": user_name,
                    "path": os.path.join(settings.MEDIA_ROOT, video.storage_key),
                    "duration_seconds": video.duration_seconds,
                    "order": video.display_order or idx,
                })

            config_data = None
            if comp.config:
                try:
                    config_data = json.loads(comp.config)
                except (json.JSONDecodeError, TypeError):
                    config_data = comp.config

            payload = {
                "compilation_id": comp.id,
                "room_id": comp.room_id,
                "room_name": room.room_name if room else "",
                "celebrant_name": room.celebrant_id if room else None,
                "template_id": comp.template_id,
                "config": config_data,
                "output_path": os.path.join(
                    settings.MEDIA_ROOT,
                    storage_key_for_final(comp.room_id, comp.id),
                ),
                "clips": clip_list,
            }
            return True, "Job claimed", payload

        except Exception as e:
            db.rollback()
            return False, f"Claim failed: {str(e)}", None

    @staticmethod
    def record_result(
        db: Session,
        compilation_id: str,
        status: str,
        storage_key: Optional[str] = None,
        error_message: Optional[str] = None,
        video_count: Optional[int] = None,
    ) -> Tuple[bool, str, None]:
        try:
            comp = VideoRepository.get_compilation_by_id(db, compilation_id)
            if not comp:
                return False, "Compilation not found", None

            if status == "completed":
                comp.status = CompilationStatus.COMPLETED
                comp.storage_key = storage_key
                comp.completed_at = datetime.utcnow()
                if video_count is not None:
                    comp.video_count = video_count
            elif status == "failed":
                comp.status = CompilationStatus.FAILED
                comp.error_message = error_message
            else:
                return False, f"Unknown status: {status}", None

            db.commit()
            return True, "Result recorded", None

        except Exception as e:
            db.rollback()
            return False, f"Failed to record result: {str(e)}", None
