# Built-in default mapping for image styles to recommended Stable Diffusion and other image models

IMAGE_MODEL_DEFAULTS = {
    # Stable Diffusion (local)
    'general': 'runwayml/stable-diffusion-v1-5',  # Good all-purpose, default
    'photorealistic': 'stabilityai/stable-diffusion-xl-base-1.0',  # Best for realism, SDXL
    'concept_art': 'CompVis/stable-diffusion-v1-4',  # Good for concept art, creative
    'cartoon': 'ai-characters/st-AI-le',  # Multi-style cartoon/anime/Disney/Ghibli
    'anime': 'stablediffusionapi/anything-v5',  # Best for anime/manga
    # DALL-E (OpenAI API)
    'dalle2': 'dall-e-2',  # DALL-E 2, creative, fast
    'dalle3': 'dall-e-3',  # DALL-E 3, best for prompt adherence, text, illustration
    # Unsplash (stock photo fallback)
    'stock': 'unsplash'  # Use for real-world stock images if all else fails
} 