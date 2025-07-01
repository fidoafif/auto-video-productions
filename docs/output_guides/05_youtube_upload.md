# Auto-upload to YouTube (Plan E)

This document details the process and standards for automated YouTube uploads in the video production pipeline.

## Main Output Files
- `outputs/<run>/video/final_video.mp4` — Input for upload
- `outputs/<run>/video/publish.json` — YouTube metadata and upload result
- `outputs/<run>/video/video_report.json` — Updated with YouTube info

## 1. Automated Upload
- Use the YouTube Data API to upload `final_video.mp4`.
- Required metadata (from script and config):
  - `title`, `description`, `tags`, `privacy`, `category`, `language`, etc.
- Credentials and settings are provided via CLI/config or `.env`.
- Log upload status and resulting YouTube URL.

### Example `publish.json`
```json
{
  "youtube_url": "https://youtu.be/abc123xyz",
  "youtube_id": "abc123xyz",
  "title": "The Loving Vegetables for Kids",
  "description": "A fun, educational video about vegetables for children.",
  "tags": ["vegetables", "kids", "education"],
  "privacy": "public",
  "upload_status": "success",
  "uploaded_at": "2024-06-01T12:34:56Z"
}
```

## 2. Post-upload Actions
- Update `video_report.json` or `publish.json` with YouTube URL and video ID.
- Optionally notify user or trigger downstream automation.

## Implementation Notes
- Upload logic should be modular and testable.
- Document required API setup and provide sample outputs in a `samples/` directory. 