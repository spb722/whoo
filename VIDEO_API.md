# Video Upload & Auto-Stitch — API Reference

> Base URL: `http://localhost:8000/api/v1`  
> All responses follow the envelope: `{ "statusCode": 200, "status": "success", "message": "...", "payload": {...} }`

---

## Authentication

All **frontend** endpoints require a JWT in the `Authorization` header:
```
Authorization: Bearer <access_token>
```

**Internal** worker endpoints use a shared secret instead of JWT:
```
X-Worker-Key: <WORKER_API_KEY>
```

---

## Prerequisites for testing

Before uploading videos, the user must be an **approved participant** of the room.

1. Create a room
2. Invite the test user to that room (or join via public room)
3. Approve the participant — this also auto-sets `expected_uploader_count` on the room
4. Optionally set `upload_deadline` on the room to test the scheduler trigger

---

## Endpoints

### 1. Upload a video clip

```
POST /rooms/{room_id}/videos
```

Streams a file to disk. Rejects if > 50 MB or if the user is not an approved participant.  
If the user already uploaded a clip for this room, it is **replaced**.  
When the uploaded count reaches `expected_uploader_count`, stitching is queued automatically.

**Headers**
```
Authorization: Bearer <token>
Content-Type: multipart/form-data
```

**Form fields**

| Field | Type | Required | Description |
|---|---|---|---|
| `file` | file | Yes | `.mp4` video file (max 50 MB) |
| `duration` | float | No | Clip duration in seconds |

**Request (curl)**
```bash
curl -X POST "http://localhost:8000/api/v1/rooms/ROOM_ID/videos" \
  -H "Authorization: Bearer TOKEN" \
  -F "file=@/path/to/clip.mp4" \
  -F "duration=18.5"
```

**Success response `200`**
```json
{
  "statusCode": 200,
  "status": "success",
  "message": "Video uploaded successfully",
  "payload": {
    "video_id": "a1b2c3d4-...",
    "room_id": "ROOM_ID",
    "user_id": 42,
    "playback_url": "https://api.whoo.app/media/rooms/ROOM_ID/raw/a1b2c3d4.mp4",
    "duration_seconds": 18.5,
    "file_size_bytes": 4194304,
    "status": "uploaded",
    "created_at": "2026-05-30T10:00:00Z"
  }
}
```

**Error responses**

| Status | Reason |
|---|---|
| `400` | File exceeds 50 MB limit |
| `400` | User is not an approved participant |
| `404` | Room not found |

---

### 2. List all clips in a room

```
GET /rooms/{room_id}/videos
```

Returns all uploaded clips for the room, ordered by `display_order` then `created_at`.

**Headers**
```
Authorization: Bearer <token>
```

**Request (curl)**
```bash
curl "http://localhost:8000/api/v1/rooms/ROOM_ID/videos" \
  -H "Authorization: Bearer TOKEN"
```

**Success response `200`**
```json
{
  "statusCode": 200,
  "status": "success",
  "message": "Videos retrieved",
  "payload": [
    {
      "video_id": "a1b2c3d4-...",
      "room_id": "ROOM_ID",
      "user_id": 42,
      "playback_url": "https://api.whoo.app/media/rooms/ROOM_ID/raw/a1b2c3d4.mp4",
      "duration_seconds": 18.5,
      "file_size_bytes": 4194304,
      "status": "uploaded",
      "created_at": "2026-05-30T10:00:00Z"
    }
  ]
}
```

**Error responses**

| Status | Reason |
|---|---|
| `404` | Room not found |

---

### 3. Get my clip for a room

```
GET /rooms/{room_id}/videos/me
```

Returns the current user's clip for this room, or `404` if they haven't uploaded one yet.

**Headers**
```
Authorization: Bearer <token>
```

**Request (curl)**
```bash
curl "http://localhost:8000/api/v1/rooms/ROOM_ID/videos/me" \
  -H "Authorization: Bearer TOKEN"
```

**Success response `200`**
```json
{
  "statusCode": 200,
  "status": "success",
  "message": "Video retrieved",
  "payload": {
    "video_id": "a1b2c3d4-...",
    "room_id": "ROOM_ID",
    "user_id": 42,
    "playback_url": "https://api.whoo.app/media/rooms/ROOM_ID/raw/a1b2c3d4.mp4",
    "duration_seconds": 18.5,
    "file_size_bytes": 4194304,
    "status": "uploaded",
    "created_at": "2026-05-30T10:00:00Z"
  }
}
```

**Error responses**

| Status | Reason |
|---|---|
| `404` | User has not uploaded a clip for this room |

---

### 4. Delete my clip

```
DELETE /rooms/{room_id}/videos/{video_id}
```

Deletes the file from disk and removes the DB row. Only the clip's owner can delete it.

**Headers**
```
Authorization: Bearer <token>
```

**Request (curl)**
```bash
curl -X DELETE "http://localhost:8000/api/v1/rooms/ROOM_ID/videos/VIDEO_ID" \
  -H "Authorization: Bearer TOKEN"
```

**Success response `200`**
```json
{
  "statusCode": 200,
  "status": "success",
  "message": "Video deleted",
  "payload": null
}
```

**Error responses**

| Status | Reason |
|---|---|
| `403` | Trying to delete another user's clip |
| `404` | Video not found or doesn't belong to this room |

---

### 5. Save compilation config

```
POST /rooms/{room_id}/compilation
```

Saves the template and optional config for the final stitched video. Only the **room owner** can call this.  
This does **not** start stitching — it only stores the config so the worker knows how to render the video.  
Stitching starts automatically when all clips are uploaded or the deadline passes.

**Headers**
```
Authorization: Bearer <token>
Content-Type: application/json
```

**Request body**

| Field | Type | Required | Description |
|---|---|---|---|
| `template_id` | string | Yes | Template name (e.g. `"classic_cake"`, `"default"`) |
| `config` | object | No | Arbitrary JSON passed as-is to the JS worker |

**Request (curl)**
```bash
curl -X POST "http://localhost:8000/api/v1/rooms/ROOM_ID/compilation" \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "template_id": "classic_cake",
    "config": {
      "background_music": "happy_birthday",
      "layout": "circle",
      "show_names": true
    }
  }'
```

**Success response `200`**
```json
{
  "statusCode": 200,
  "status": "success",
  "message": "Compilation config saved",
  "payload": {
    "template_id": "classic_cake"
  }
}
```

**Error responses**

| Status | Reason |
|---|---|
| `403` | Caller is not the room owner |
| `404` | Room not found |

---

### 6. Get compilation status

```
GET /rooms/{room_id}/compilation
```

Returns the current state of the stitched video. Poll this after all clips are uploaded.  
`video_url` is only present when `status` is `"completed"`.

**Headers**
```
Authorization: Bearer <token>
```

**Request (curl)**
```bash
curl "http://localhost:8000/api/v1/rooms/ROOM_ID/compilation" \
  -H "Authorization: Bearer TOKEN"
```

**Response — not started yet `200`**
```json
{
  "statusCode": 200,
  "status": "success",
  "message": "No compilation yet",
  "payload": null
}
```

**Response — in progress `200`**
```json
{
  "statusCode": 200,
  "status": "success",
  "message": "Compilation status retrieved",
  "payload": {
    "compilation_id": "z9y8x7w6-...",
    "room_id": "ROOM_ID",
    "status": "processing",
    "video_count": 3,
    "video_url": null,
    "error_message": null,
    "created_at": "2026-05-30T10:05:00Z",
    "completed_at": null
  }
}
```

**Response — completed `200`**
```json
{
  "statusCode": 200,
  "status": "success",
  "message": "Compilation status retrieved",
  "payload": {
    "compilation_id": "z9y8x7w6-...",
    "room_id": "ROOM_ID",
    "status": "completed",
    "video_count": 3,
    "video_url": "https://api.whoo.app/media/rooms/ROOM_ID/final/z9y8x7w6.mp4",
    "error_message": null,
    "created_at": "2026-05-30T10:05:00Z",
    "completed_at": "2026-05-30T10:07:34Z"
  }
}
```

**Response — failed `200`**
```json
{
  "statusCode": 200,
  "status": "success",
  "message": "Compilation status retrieved",
  "payload": {
    "compilation_id": "z9y8x7w6-...",
    "room_id": "ROOM_ID",
    "status": "failed",
    "video_count": 3,
    "video_url": null,
    "error_message": "ffmpeg exited with code 1",
    "created_at": "2026-05-30T10:05:00Z",
    "completed_at": null
  }
}
```

**Compilation status values**

| Value | Meaning |
|---|---|
| `pending` | Queued — worker hasn't picked it up yet |
| `processing` | Worker is actively stitching |
| `completed` | Done — `video_url` is available |
| `failed` | Worker reported an error — see `error_message` |

**Error responses**

| Status | Reason |
|---|---|
| `404` | Room not found |

---

## Internal Worker Endpoints

These are **not** for the frontend. They are called by the JS stitching worker.

### 7. Claim the next job

```
POST /internal/compilations/claim
```

Atomically picks the oldest `pending` compilation, marks it `processing`, and returns everything the worker needs.  
Returns `204 No Content` when the queue is empty.

**Headers**
```
X-Worker-Key: <WORKER_API_KEY>
```

**Request (curl)**
```bash
curl -X POST "http://localhost:8000/api/v1/internal/compilations/claim" \
  -H "X-Worker-Key: your-worker-secret"
```

**Response — job available `200`**
```json
{
  "statusCode": 200,
  "status": "success",
  "message": "Job claimed",
  "payload": {
    "compilation_id": "z9y8x7w6-...",
    "room_id": "ROOM_ID",
    "room_name": "Sam's Birthday",
    "celebrant_name": "Sam",
    "template_id": "classic_cake",
    "config": {
      "background_music": "happy_birthday",
      "layout": "circle"
    },
    "output_path": "/var/whoo/media/rooms/ROOM_ID/final/z9y8x7w6.mp4",
    "clips": [
      {
        "video_id": "a1b2c3d4-...",
        "user_name": "Alex",
        "path": "/var/whoo/media/rooms/ROOM_ID/raw/a1b2c3d4.mp4",
        "duration_seconds": 18.5,
        "order": 1
      },
      {
        "video_id": "d4e5f6g7-...",
        "user_name": "Maya",
        "path": "/var/whoo/media/rooms/ROOM_ID/raw/d4e5f6g7.mp4",
        "duration_seconds": 22.0,
        "order": 2
      }
    ]
  }
}
```

**Response — nothing pending `204`**
```
(empty body)
```

**Error responses**

| Status | Reason |
|---|---|
| `403` | Missing or incorrect `X-Worker-Key` |

---

### 8. Report job result

```
POST /internal/compilations/{compilation_id}/result
```

Called by the worker after it finishes (success or failure).

**Headers**
```
X-Worker-Key: <WORKER_API_KEY>
Content-Type: application/json
```

**Request body — on success**

| Field | Type | Required | Description |
|---|---|---|---|
| `status` | string | Yes | Must be `"completed"` |
| `storage_key` | string | Yes | Relative path of output file, e.g. `"rooms/ROOM_ID/final/z9y8x7w6.mp4"` |
| `video_count` | integer | No | Number of clips included in the final video |

**Request body — on failure**

| Field | Type | Required | Description |
|---|---|---|---|
| `status` | string | Yes | Must be `"failed"` |
| `error_message` | string | No | What went wrong |

**Request (curl) — success**
```bash
curl -X POST "http://localhost:8000/api/v1/internal/compilations/COMPILATION_ID/result" \
  -H "X-Worker-Key: your-worker-secret" \
  -H "Content-Type: application/json" \
  -d '{
    "status": "completed",
    "storage_key": "rooms/ROOM_ID/final/z9y8x7w6.mp4",
    "video_count": 3
  }'
```

**Request (curl) — failure**
```bash
curl -X POST "http://localhost:8000/api/v1/internal/compilations/COMPILATION_ID/result" \
  -H "X-Worker-Key: your-worker-secret" \
  -H "Content-Type: application/json" \
  -d '{
    "status": "failed",
    "error_message": "ffmpeg exited with code 1"
  }'
```

**Success response `200`**
```json
{
  "statusCode": 200,
  "status": "success",
  "message": "Result recorded",
  "payload": null
}
```

**Error responses**

| Status | Reason |
|---|---|
| `400` | Compilation ID not found or unknown status value |
| `403` | Missing or incorrect `X-Worker-Key` |

---

## End-to-end test flow

Use this sequence to verify the full feature from scratch.

### Step 1 — Set up (use existing room APIs)
```
POST /api/v1/rooms              → create a room, note room_id
POST /api/v1/rooms/{id}/invite  → invite 2 test users
PUT  /api/v1/rooms/{id}/participants/{user_id}  → approve both
                                  (expected_uploader_count auto-becomes 3 — owner + 2)
```

### Step 2 — Save compilation config (optional, do before uploads)
```
POST /api/v1/rooms/{room_id}/compilation
Body: { "template_id": "classic_cake", "config": { "layout": "circle" } }
```

### Step 3 — Upload clips (as each participant)
```
POST /api/v1/rooms/{room_id}/videos   ← file + duration
```
After the 3rd upload, `GET /compilation` should show `status: "pending"`.

### Step 4 — Simulate the JS worker
```bash
# Claim the job
curl -X POST ".../internal/compilations/claim" -H "X-Worker-Key: ..."

# (worker does its work — creates the output file)

# Report success
curl -X POST ".../internal/compilations/COMPILATION_ID/result" \
  -H "X-Worker-Key: ..." \
  -d '{"status":"completed","storage_key":"rooms/ROOM_ID/final/COMPILATION_ID.mp4"}'
```

### Step 5 — Verify the final video
```
GET /api/v1/rooms/{room_id}/compilation
→ status: "completed", video_url: "https://..."
```

---

## Testing the deadline trigger (alternative to step 3)

To test stitching via deadline instead of waiting for all uploads:

1. Set `upload_deadline` to a past timestamp when creating/updating the room
2. Wait up to 60 seconds for the scheduler to run
3. `GET /compilation` should show `status: "pending"` without all clips being uploaded

---

## Notes for the UI team

- **Re-upload is safe:** Uploading again replaces the previous clip for that user. The `video_id` will change.
- **Poll interval:** Poll `GET /compilation` every 5–10 seconds while `status` is `pending` or `processing`. Stop when it becomes `completed` or `failed`.
- **`video_url` is only present when `status == "completed"`** — don't try to render it otherwise.
- **Swagger UI** is available at `http://localhost:8000/api/v1/openapi.json` (interactive docs at `/docs`).
