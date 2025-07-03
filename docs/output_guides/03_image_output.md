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
    "resolution": "1024x1024",
    "model": "ai-characters/st-AI-le"
  },
  ...
]
```

#### Field Details
- **filename** (string, required): Name of the image file (e.g., `01_Intro.png`).
- **prompt** (string, required): The prompt or description used to generate the image.
- **alt_text** (string, required): Alt text for accessibility and SEO, describing the image content.
- **resolution** (string, required): Image resolution (e.g., `1024x1024`).
- **model** (string, required): The model used to generate the image.

## 2. Alt Text for Accessibility
- Alt text should be concise, descriptive, and meaningful for users who cannot see the image.
- Alt text is used by screen readers and improves searchability.

### Example Alt Text
```
Cartoon vegetables dancing together
```

## 3. Branding
- Optionally add watermarks or overlays to images for branding and IP protection.

## 4. Dynamic Model Selection (Optional & Default)
- The pipeline supports dynamic model selection for each image section.
- In `input.json`, you can optionally set advanced fields under `meta.image`:
  - `engine` (string): Set to `"dynamic"` to enable per-image model selection. If not provided, defaults to `"dynamic"`.
  - `default_model` (string): The fallback model if no style/model is specified. Defaults to `"runwayml/stable-diffusion-v1-5"`.
  - `size` (string): Image resolution (e.g., `"512x512"`). Defaults to `"512x512"`.
  - `quality` (string): Image quality setting. Defaults to `"standard"`.
  - `models` (object): Mapping of style names to model IDs. Optional; if not provided, only the default model is used.
- Each section in the script can specify a `style` (or `model`) field to select the best model for that image.
- The pipeline will use the specified model for each image, falling back to the default if not specified.
- The `images.json` manifest will include a `model` field for each image, documenting which model was used.

### Example `input.json` (with dynamic image models)
```json
"image": {
  "engine": "dynamic",
  "default_model": "runwayml/stable-diffusion-v1-5",
  "size": "512x512",
  "quality": "standard",
  "models": {
    "cartoon": "ai-characters/st-AI-le",
    "photorealistic": "stabilityai/stable-diffusion-xl-base-1.0",
    "anime": "stablediffusionapi/anything-v5"
  }
}
```

### Example `input.json` (minimal, all fields omitted)
```json
"image": {}
```

### Example Section
```json
{
  "heading": "Magical Garden",
  "narration": "A magical garden full of talking fruit.",
  "style": "cartoon"
}
```

### Example Manifest Entry
```json
{
  "filename": "01_Magical_Garden.png",
  "prompt": "A magical garden full of talking fruit.",
  "alt_text": "Cartoon magical garden with talking fruit",
  "resolution": "512x512",
  "model": "ai-characters/st-AI-le"
}
```

## Best Practices
- All advanced image config fields in `input.json` are optional. The system will use dynamic model selection and sensible defaults if not provided.
- Ensure all image files and manifest entries are named consistently and match the section order in the script.
- Validate that every image file has a corresponding entry in `images.json` with complete metadata.
- Store all outputs in `outputs/<run>/images/`.
- Metadata and branding logic should be modular and testable.
- Document the manifest and provide sample outputs in a `samples/` directory. 