# Audio Output Improvements (Plan B)

This document details the improvements and standards for audio-related outputs in the video production pipeline.

## Main Output Files
- `outputs/<run>/audio/01_Intro.wav`, ... — Main audio segments (WAV)
- `outputs/<run>/audio/01_Intro.txt`, ... — Transcript per segment
- `outputs/<run>/audio/voice.json` — Audio manifest and metadata

## 1. Consistent Naming and Metadata
- Filenames follow the pattern: `NN_SectionHeading.wav` (e.g., `01_Intro.wav`).
- `voice.json` is a manifest containing metadata for each audio segment.

### Example `voice.json`
```json
[
  {
    "filename": "01_Intro.wav",
    "duration": 12.0,
    "speaker": "default",
    "text": "Welcome to our video!",
    "format": "wav"
  },
  ...
]
```

#### Field Details
- **filename** (string, required): Name of the audio file (e.g., `01_Intro.wav`).
- **duration** (number, required): Duration of the audio segment in seconds.
- **speaker** (string, optional): Name or identifier of the speaker/voice used.
- **text** (string, required): The narration text spoken in this segment.
- **format** (string, required): Audio format (always `wav`).

## 2. Accessibility: Transcript Files
- For each audio segment, generate a transcript file (`.txt`) with the narration text.
- Transcripts improve accessibility, enable search, and support captioning.

### Example Transcript (`01_Intro.txt`)
```
Welcome to our video!
```

## 3. Best Practices
- Ensure all audio files and transcripts are named consistently and match the section order in the script.
- Validate that every audio file has a corresponding entry in `voice.json` and a transcript file.
- Store all outputs in `outputs/<run>/audio/`.
- Metadata and transcript generation should be modular and testable.
- Document the manifest and provide sample outputs in a `samples/` directory. 