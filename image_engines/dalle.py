import os
import requests
from PIL import Image
from io import BytesIO
from dotenv import load_dotenv

def generate_dalle_image(prompt: str, output_path: str, model: str = "dall-e-3", size: str = "1024x1024", quality: str = "standard") -> None:
    """
    Generate an image using OpenAI's DALL-E API.
    
    Args:
        prompt (str): The text prompt for image generation
        output_path (str): Path to save the generated image
        model (str): DALL-E model to use (dall-e-2, dall-e-3)
        size (str): Image size (1024x1024, 1792x1024, 1024x1792 for DALL-E-3)
        quality (str): Image quality (standard, hd for DALL-E-3)
    """
    load_dotenv()
    api_key = os.getenv("OPENAI_API_KEY")
    
    if not api_key:
        raise EnvironmentError("OPENAI_API_KEY not found in environment variables")
    
    # API endpoint
    url = "https://api.openai.com/v1/images/generations"
    
    # Prepare the request
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    data = {
        "model": model,
        "prompt": prompt,
        "n": 1,
        "size": size
    }
    
    # Add quality parameter for DALL-E-3
    if model == "dall-e-3":
        data["quality"] = quality
    
    try:
        print(f"Generating DALL-E image with model: {model}")
        response = requests.post(url, headers=headers, json=data, timeout=60)
        response.raise_for_status()
        
        result = response.json()
        
        if "data" in result and len(result["data"]) > 0:
            image_url = result["data"][0]["url"]
            
            # Download the image
            image_response = requests.get(image_url, timeout=30)
            image_response.raise_for_status()
            
            # Save the image
            with open(output_path, "wb") as f:
                f.write(image_response.content)
            
            print(f"\u2713 DALL-E image generated and saved to: {output_path}")
        else:
            raise RuntimeError("No image data received from DALL-E API")
            
    except requests.exceptions.RequestException as e:
        if "quota" in str(e).lower() or "limit" in str(e).lower():
            raise RuntimeError("OpenAI API quota or rate limit exceeded")
        raise RuntimeError(f"DALL-E API request failed: {str(e)}")
    except Exception as e:
        raise RuntimeError(f"Failed to generate DALL-E image: {str(e)}") 