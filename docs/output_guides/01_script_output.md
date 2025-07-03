# Script Output Improvements (Plan A)

This document details the improvements and standards for script-related outputs in the video production pipeline.

## Main Output Files
- `outputs/<run>/scripts/script.json` — Main structured script output
- `outputs/<run>/scripts/script.srt` — Subtitles (SRT)

## 1. Strict Schema Validation
- All `script.json` files must conform to a defined JSON Schema (see `schemas/script.schema.json`).
- Validation is performed after script generation; invalid outputs are logged and rejected.

### Complete Example Schema
```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "Video Script",
  "type": "object",
  "required": ["title", "sections", "meta"],
  "properties": {
    "title": { "type": "string" },
    "sections": {
      "type": "array",
      "minItems": 1,
      "items": {
        "type": "object",
        "required": ["heading", "narration", "duration"],
        "properties": {
          "heading": { "type": "string" },
          "narration": { "type": "string" },
          "duration": { "type": "number", "minimum": 1 }
    }
      }
    },
  "meta": {
      "type": "object",
      "required": ["model", "generated_at"],
      "properties": {
        "language": { "type": "string" },
        "target_age": { "type": "string" },
        "tags": { "type": "array", "items": { "type": "string" } },
        "estimated_reading_level": { "type": "string" },
        "created_by": { "type": "string" },
        "model": { "type": "string" },
        "generated_at": { "type": "string", "format": "date-time" }
      }
    }
  }
}
```

#### Field Details
- **title** (string, required): The overall title of the script/video.
- **sections** (array, required): List of script sections. Each section must have:
  - **heading** (string, required): The section title or heading.
  - **narration** (string, required): The narration text for this section.
  - **duration** (number, required): Estimated or actual duration in seconds (must be >= 1).
- **meta** (object, required): Metadata about the script and generation process. Should include:
  - **language** (string, optional): Language of the script (e.g., "en").
  - **target_age** (string, optional): Intended audience age group.
  - **tags** (array of strings, optional): Keywords or tags for the script.
  - **estimated_reading_level** (string, optional): Reading level (e.g., "Grade 3").
  - **created_by** (string, optional): Name or identifier of the script creator or system.
  - **model** (string, required): Model or engine used for generation.
  - **generated_at** (string, required, date-time): ISO timestamp of when the script was generated.

## 2. Section Consistency
- Each script must have multiple, well-formed sections.
- Logic should split/merge sections as needed to avoid single-section or malformed outputs.

## 3. Rich Metadata
- The `meta` field should include:
  - `language`, `target_age`, `tags`, `estimated_reading_level`, `created_by`, `model`, `generated_at`, etc.
- Metadata is used for analytics, search, and downstream automation.

## 4. SRT Export (Subtitles)
- After validation, export the script as SRT for subtitles.

### Example SRT (Subtitles)
```
1
00:00:00,000 --> 00:00:12,000
[Section Heading]
Narration text here.

2
00:00:12,000 --> 00:00:24,000
[Next Section Heading]
...
```

## Implementation Notes
- All exports are saved in `outputs/<run>/scripts/`.
- Validation and export should be modular and testable.
- Document the schema and provide sample outputs in a `samples/` directory. 