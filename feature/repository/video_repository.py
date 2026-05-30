from typing import Optional, List
from datetime import datetime
from sqlalchemy.orm import Session

from feature.models.video import RoomVideo, RoomCompilation, VideoStatus, CompilationStatus
from feature.models.room import Room, RoomParticipant


class VideoRepository:

    @staticmethod
    def save_video(db: Session, video: RoomVideo) -> RoomVideo:
        db.add(video)
        db.commit()
        db.refresh(video)
        return video

    @staticmethod
    def get_video_by_id(db: Session, video_id: str) -> Optional[RoomVideo]:
        return db.query(RoomVideo).filter(RoomVideo.id == video_id).first()

    @staticmethod
    def get_videos_for_room(db: Session, room_id: str) -> List[RoomVideo]:
        return (
            db.query(RoomVideo)
            .filter(RoomVideo.room_id == room_id, RoomVideo.status == VideoStatus.UPLOADED)
            .order_by(RoomVideo.display_order, RoomVideo.created_at)
            .all()
        )

    @staticmethod
    def get_video_for_user(db: Session, room_id: str, user_id: int) -> Optional[RoomVideo]:
        return (
            db.query(RoomVideo)
            .filter(RoomVideo.room_id == room_id, RoomVideo.user_id == user_id)
            .first()
        )

    @staticmethod
    def count_uploaded_clips(db: Session, room_id: str) -> int:
        return (
            db.query(RoomVideo)
            .filter(RoomVideo.room_id == room_id, RoomVideo.status == VideoStatus.UPLOADED)
            .count()
        )

    @staticmethod
    def delete_video(db: Session, video: RoomVideo) -> None:
        db.delete(video)
        db.commit()

    @staticmethod
    def get_rooms_past_deadline_without_compilation(db: Session, now: datetime) -> List[Room]:
        return (
            db.query(Room)
            .outerjoin(RoomCompilation, RoomCompilation.room_id == Room.id)
            .filter(Room.upload_deadline <= now, RoomCompilation.id == None)  # noqa: E711
            .all()
        )

    @staticmethod
    def get_compilation_for_room(db: Session, room_id: str) -> Optional[RoomCompilation]:
        return db.query(RoomCompilation).filter(RoomCompilation.room_id == room_id).first()

    @staticmethod
    def get_compilation_by_id(db: Session, compilation_id: str) -> Optional[RoomCompilation]:
        return db.query(RoomCompilation).filter(RoomCompilation.id == compilation_id).first()

    @staticmethod
    def claim_next_pending_job(db: Session) -> Optional[RoomCompilation]:
        comp = (
            db.query(RoomCompilation)
            .filter(RoomCompilation.status == CompilationStatus.PENDING)
            .order_by(RoomCompilation.created_at)
            .with_for_update(skip_locked=True)
            .first()
        )
        if comp:
            comp.status = CompilationStatus.PROCESSING
            db.commit()
            db.refresh(comp)
        return comp

    @staticmethod
    def get_stale_processing_jobs(db: Session, cutoff_time: datetime) -> List[RoomCompilation]:
        return (
            db.query(RoomCompilation)
            .filter(
                RoomCompilation.status == CompilationStatus.PROCESSING,
                RoomCompilation.updated_at <= cutoff_time,
            )
            .all()
        )

    @staticmethod
    def save_compilation(db: Session, comp: RoomCompilation) -> RoomCompilation:
        db.add(comp)
        db.commit()
        db.refresh(comp)
        return comp

    @staticmethod
    def get_approved_participant(db: Session, room_id: str, user_id: int) -> Optional[RoomParticipant]:
        return (
            db.query(RoomParticipant)
            .filter(
                RoomParticipant.room_id == room_id,
                RoomParticipant.user_id == user_id,
                RoomParticipant.status == "approved",
            )
            .first()
        )

    @staticmethod
    def get_clips_with_users(db: Session, room_id: str):
        from app.models.user import User
        return (
            db.query(RoomVideo, User)
            .join(User, User.id == RoomVideo.user_id)
            .filter(RoomVideo.room_id == room_id, RoomVideo.status == VideoStatus.UPLOADED)
            .order_by(RoomVideo.display_order, RoomVideo.created_at)
            .all()
        )
