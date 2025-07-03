import torch
from diffusers import StableDiffusionPipeline

prompt = "A fantasy landscape, trending on artstation"
model = "runwayml/stable-diffusion-v1-5"

if torch.backends.mps.is_available():
    device = "mps"
    dtype = torch.float16
elif torch.cuda.is_available():
    device = "cuda"
    dtype = torch.float16
else:
    device = "cpu"
    dtype = torch.float32

pipe = StableDiffusionPipeline.from_pretrained(
    model,
    torch_dtype=dtype,
    safety_checker=None
)
pipe = pipe.to(device)

image = pipe(prompt, num_inference_steps=20, guidance_scale=7.5).images[0]
image.save("test_sd_m1.png")
print("Image saved as test_sd_m1.png") 