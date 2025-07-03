# Stable Diffusion Model Guide

A curated reference for popular Stable Diffusion models, their Hugging Face IDs, and the best use case for each style (cartoon, anime, photorealistic, etc.).

---

## Model Overview

| Model Name / Hugging Face ID                | Best Use Case                                      |
|---------------------------------------------|----------------------------------------------------|
| **CompVis/stable-diffusion-v1-4**           | General, photorealistic, concept art               |
| **runwayml/stable-diffusion-v1-5**          | General, improved faces/details                    |
| **stabilityai/stable-diffusion-2-1**        | High-res, landscapes, modern scenes                |
| **stabilityai/stable-diffusion-xl-base-1.0**| Photorealism, complex scenes, commercial           |
| **stablediffusionapi/anything-v5**          | Anime, manga, cartoon                              |
| **ai-characters/st-AI-le**                  | Multi-style cartoon/anime/Disney/Ghibli            |
| **stabilityai/stable-diffusion-3.5-large-turbo** | Fast, high-quality, general-purpose           |
| **Ketengan-Diffusion/SomniumSC-v1**         | 2D cartoon, fantasy, vibrant illustrations         |

---

## Model Details

### CompVis/stable-diffusion-v1-4
- **Best for:** General-purpose, photorealistic images, concept art, illustrations, creative prompts.
- **Description:** The classic, most widely used SD 1.x model. Good for a wide range of prompts, but not highly specialized.

### runwayml/stable-diffusion-v1-5
- **Best for:** General-purpose, slightly improved photorealism and prompt adherence over v1-4.
- **Description:** The default for many pipelines, with better fine details and faces than v1-4.

### stabilityai/stable-diffusion-2-1
- **Best for:** Higher-resolution images, improved landscapes, architecture, and more modern styles.
- **Description:** Trained on a larger dataset, better at 768x768 images, but sometimes less creative for fantasy or anime.

### stabilityai/stable-diffusion-xl-base-1.0 (SDXL)
- **Best for:** High-quality, photorealistic images, complex scenes, and commercial use.
- **Description:** The latest official model, excels at realism, text rendering, and complex compositions.

### stablediffusionapi/anything-v5 (Anime/Cartoon)
- **Best for:** Anime, manga, cartoon, and stylized character art.
- **Description:** Fine-tuned for anime and cartoon styles, great for characters, waifus, and vibrant scenes.

### ai-characters/st-AI-le
- **Best for:** Multiple cartoon, anime, Ghibli, Disney, and stylized character art in one model.
- **Description:** Trained for a wide range of cartoon and anime styles, including Ghibli, Disney, Clone Wars, and more.

### stabilityai/stable-diffusion-3.5-large-turbo
- **Best for:** Fast, high-quality, general-purpose images, including photorealism and complex prompts.
- **Description:** Latest SD3.5 model, improved prompt understanding, typography, and image quality.

### Ketengan-Diffusion/SomniumSC-v1
- **Best for:** 2D cartoonish/fantasy art, vibrant and aesthetic illustrations.
- **Description:** Fine-tuned for 2D, cartoon, and fantasy styles, optimized for non-realistic, colorful images.

---

## How to Add a New Stable Diffusion Model

You can easily add new models (from Hugging Face or custom checkpoints) to your pipeline. Here's how:

### 1. **Find the Model**
- Browse [Hugging Face Models](https://huggingface.co/models?pipeline_tag=text-to-image&search=stable-diffusion) for a model that fits your needs (e.g., anime, photorealistic, fantasy).
- Copy the model's repository name (e.g., `stabilityai/stable-diffusion-xl-base-1.0`).

### 2. **Update the Model Name in Your Pipeline**
- In your code (e.g., `image_engines/stable_diffusion.py`), change the `model` argument to the new model name:
  ```python
  generate_sd_image(prompt, output_path, model="stabilityai/stable-diffusion-xl-base-1.0")
  ```
- Or, if your pipeline supports passing the model name via config or CLI, update it there.

### 3. **(Optional) Download the Model Locally**
- The first time you use a new model, it will be downloaded automatically from Hugging Face.
- For custom or private models, ensure you have access rights or download the weights manually.

### 4. **Test the Model**
- Run your pipeline or the test script to verify the new model works and produces the desired style.
- Adjust prompt style or model parameters as needed for best results.

### 5. **Best Practices**
- **Photorealism:** Use SDXL or SD3.5 models.
- **Anime/Cartoon:** Use Anything-v5, st-AI-le, or SomniumSC-v1.
- **General/Creative:** Use v1-5, v1-4, or SD3.5.
- **High-res:** Use SD2.1 or SDXL.
- **Check model license** for commercial use if needed.

---

## Quick Tips
- For **anime/cartoons**: use `anything-v5`, `st-AI-le`, or `SomniumSC-v1`.
- For **photorealism**: use `stable-diffusion-xl-base-1.0` or `stable-diffusion-3.5-large-turbo`.
- For **general/creative**: use `runwayml/stable-diffusion-v1-5` or `CompVis/stable-diffusion-v1-4`.

---

*Last updated: 2025-07-02* 