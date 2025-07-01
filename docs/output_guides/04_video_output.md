# Video Output Improvements (Plan D)

This document details the improvements and standards for video-related outputs in the video production pipeline.

## Main Output Files
- `outputs/<run>/video/final_video.mp4` — Final assembled video
- `outputs/<run>/video/final_video.srt` — Subtitles (SRT)
- `outputs/<run>/video/video_report.json` — Analytics and summary
- `outputs/<run>/video/video_report.csv` — Analytics (CSV)

## 1. Subtitles and Captions
- Auto-generate SRT or VTT subtitles from the script and embed in the video if desired.

### Example SRT
```
1
00:00:00,000 --> 00:00:12,000
[Section Heading]
Narration text here.
```

## 2. Intro/Outro Templates
- Allow users to specify intro/outro video or branding.
- Concatenate with main video during assembly.

## 3. Analytics
- Output a summary report (JSON/CSV) with section durations, word counts, etc.

### Example `video_report.json`
```json
{
  "title": "The Loving Vegetables for Kids",
  "total_duration": 120,
  "sections": [
    {"heading": "Intro", "duration": 12, "word_count": 20},
    ...
  ],
  "generated_at": "2024-06-01T12:00:00Z"
}
```

## Implementation Notes
- All exports are saved in `outputs/<run>/video/`.
- Subtitle, intro/outro, and analytics generation should be modular and testable.
- Document the report format and provide sample outputs in a `samples/` directory. 