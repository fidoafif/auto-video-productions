import os
from diffusers.pipelines.stable_diffusion.pipeline_stable_diffusion import StableDiffusionPipeline
import torch
from PIL import Image
import numpy as np

def generate_sd_image(prompt: str, output_path: str, model: str = "runwayml/stable-diffusion-v1-5") -> None:
    """
    Generate an image using Stable Diffusion locally.
    
    Args:
        prompt (str): The text prompt for image generation
        output_path (str): Path to save the generated image
        model (str): Model name or path (default: runwayml/stable-diffusion-v1-5)
    """
    try:
        print(f"Torch version: {torch.__version__}")
        print(f"MPS available: {torch.backends.mps.is_available()}")
        print(f"CUDA available: {torch.cuda.is_available()}")
        # Device and dtype selection for Apple Silicon, CUDA, or CPU
        if torch.cuda.is_available():
            device = "cuda"
            dtype = torch.float16
        elif torch.backends.mps.is_available():
            device = "mps"
            dtype = torch.float32  # float32 is safer for MPS
        else:
            device = "cpu"
            dtype = torch.float32
        print(f"Using device: {device}, dtype: {dtype}")
        print(f"Loading Stable Diffusion model: {model}")
        
        pipe = StableDiffusionPipeline.from_pretrained(
            model,
            torch_dtype=dtype,
            safety_checker=None  # Disable safety checker for faster generation
        )
        # Force submodules to correct dtype before moving to device
        pipe.unet.to(dtype)
        pipe.vae.to(dtype)
        pipe.text_encoder.to(dtype)
            pipe = pipe.to(device)
        
        print(f"Generating Stable Diffusion image...")
        result = pipe(
            prompt=prompt,
            num_inference_steps=20,
            guidance_scale=7.5,
            width=512,
            height=512
        )
        image = None
        if not isinstance(result, tuple) and hasattr(result, 'images'):
            image = result.images[0]
        elif isinstance(result, tuple):
            img_candidate = result[0]
            if isinstance(img_candidate, Image.Image):
                image = img_candidate
            elif isinstance(img_candidate, torch.Tensor):
                arr = img_candidate.detach().cpu().numpy()
                if arr.ndim == 3 and arr.shape[0] in (1, 3):
                    arr = np.transpose(arr, (1, 2, 0))
                arr = (arr * 255).clip(0, 255).astype(np.uint8)
                image = Image.fromarray(arr)
            elif isinstance(img_candidate, np.ndarray):
                arr = img_candidate
                if arr.ndim == 3 and arr.shape[0] in (1, 3):
                    arr = np.transpose(arr, (1, 2, 0))
                arr = (arr * 255).clip(0, 255).astype(np.uint8)
                image = Image.fromarray(arr)
            else:
                raise RuntimeError("Unknown image output type from StableDiffusionPipeline")
        else:
            raise RuntimeError("Unknown output type from StableDiffusionPipeline")
        if not isinstance(image, Image.Image):
            raise RuntimeError("Output is not a PIL.Image.Image after conversion attempts")
        image.save(output_path)
        print(f"\u2713 Stable Diffusion image generated and saved to: {output_path}")
    except Exception as e:
        raise RuntimeError(f"Failed to generate Stable Diffusion image: {str(e)}") 