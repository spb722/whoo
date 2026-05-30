import os
from app.core.config import settings


def raw_path(room_id: str, video_id: str) -> str:
    rel = f"rooms/{room_id}/raw/{video_id}.mp4"
    abs_path = os.path.join(settings.MEDIA_ROOT, rel)
    os.makedirs(os.path.dirname(abs_path), exist_ok=True)
    return abs_path


def final_path(room_id: str, compilation_id: str) -> str:
    rel = f"rooms/{room_id}/final/{compilation_id}.mp4"
    abs_path = os.path.join(settings.MEDIA_ROOT, rel)
    os.makedirs(os.path.dirname(abs_path), exist_ok=True)
    return abs_path


def storage_key_for_raw(room_id: str, video_id: str) -> str:
    return f"rooms/{room_id}/raw/{video_id}.mp4"


def storage_key_for_final(room_id: str, compilation_id: str) -> str:
    return f"rooms/{room_id}/final/{compilation_id}.mp4"
