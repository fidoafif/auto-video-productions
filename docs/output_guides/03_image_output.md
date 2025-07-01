# Image Output Improvements (Plan C)

This document details the improvements and standards for image-related outputs in the video production pipeline.

## Main Output Files
- `outputs/<run>/images/01_Intro.png`, ... — Main images
- `outputs/<run>/images/images.json` — Image manifest and metadata

## 1. Metadata and Alt Text
- Each image entry in `images.json` includes:
  - `filename`, `prompt`, `alt_text`, `resolution`, etc.

### Example `images.json`
```json
[
  {
    "filename": "01_Intro.png",
    "prompt": "A group of happy vegetables dancing",
    "alt_text": "Cartoon vegetables dancing together",
    "resolution": "1024x1024"
  },
  ...
]
```

#### Field Details
- **filename** (string, required): Name of the image file (e.g., `01_Intro.png`).
- **prompt** (string, required): The prompt or description used to generate the image.
- **alt_text** (string, required): Alt text for accessibility and SEO, describing the image content.
- **resolution** (string, required): Image resolution (e.g., `1024x1024`).

## 2. Alt Text for Accessibility
- Alt text should be concise, descriptive, and meaningful for users who cannot see the image.
- Alt text is used by screen readers and improves searchability.

### Example Alt Text
```
Cartoon vegetables dancing together
```

## 3. Branding
- Optionally add watermarks or overlays to images for branding and IP protection.

## Best Practices
- Ensure all image files and manifest entries are named consistently and match the section order in the script.
- Validate that every image file has a corresponding entry in `images.json` with complete metadata.
- Store all outputs in `outputs/<run>/images/`.
- Metadata and branding logic should be modular and testable.
- Document the manifest and provide sample outputs in a `samples/` directory. 