import os
from diffusers import StableDiffusionPipeline
import torch
from PIL import Image

def generate_sd_image(prompt: str, output_path: str, model: str = "runwayml/stable-diffusion-v1-5") -> None:
    """
    Generate an image using Stable Diffusion locally.
    
    Args:
        prompt (str): The text prompt for image generation
        output_path (str): Path to save the generated image
        model (str): Model name or path (default: runwayml/stable-diffusion-v1-5)
    """
    try:
        print(f"Loading Stable Diffusion model: {model}")
        
        # Check if CUDA is available
        device = "cuda" if torch.cuda.is_available() else "cpu"
        print(f"Using device: {device}")
        
        # Load the pipeline
        pipe = StableDiffusionPipeline.from_pretrained(
            model,
            torch_dtype=torch.float16 if device == "cuda" else torch.float32,
            safety_checker=None  # Disable safety checker for faster generation
        )
        
        if device == "cuda":
            pipe = pipe.to(device)
        
        # Generate the image
        print(f"Generating Stable Diffusion image...")
        image = pipe(
            prompt=prompt,
            num_inference_steps=20,
            guidance_scale=7.5,
            width=512,
            height=512
        ).images[0]
        
        # Save the image
        image.save(output_path)
        print(f"\u2713 Stable Diffusion image generated and saved to: {output_path}")
        
    except Exception as e:
        raise RuntimeError(f"Failed to generate Stable Diffusion image: {str(e)}") 