from typing import Optional, List, Any
from datetime import datetime
from pydantic import BaseModel


class VideoUploadResponse(BaseModel):
    video_id: str
    room_id: str
    user_id: int
    playback_url: str
    duration_seconds: Optional[float]
    file_size_bytes: Optional[int]
    status: str
    created_at: Optional[datetime]

    class Config:
        orm_mode = True


class VideoListItem(BaseModel):
    video_id: str
    room_id: str
    user_id: int
    playback_url: str
    duration_seconds: Optional[float]
    file_size_bytes: Optional[int]
    status: str
    created_at: Optional[datetime]

    class Config:
        orm_mode = True


class CompilationConfigRequest(BaseModel):
    template_id: str = "default"
    config: Optional[dict] = None


class CompilationStatusResponse(BaseModel):
    compilation_id: str
    room_id: str
    status: str
    video_count: int
    video_url: Optional[str]
    error_message: Optional[str]
    created_at: Optional[datetime]
    completed_at: Optional[datetime]

    class Config:
        orm_mode = True


class WorkerClipItem(BaseModel):
    video_id: str
    user_name: str
    path: str
    duration_seconds: Optional[float]
    order: Optional[int]


class WorkerClaimResponse(BaseModel):
    compilation_id: str
    room_id: str
    room_name: str
    celebrant_name: Optional[str]
    template_id: str
    config: Optional[Any]
    output_path: str
    clips: List[WorkerClipItem]


class WorkerResultRequest(BaseModel):
    status: str
    storage_key: Optional[str] = None
    video_count: Optional[int] = None
    error_message: Optional[str] = None
