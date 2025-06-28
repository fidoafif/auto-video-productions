import os
import requests
from PIL import Image
from io import BytesIO
from dotenv import load_dotenv

def generate_unsplash_image(prompt: str, output_path: str) -> None:
    """
    Search and download an image from Unsplash based on the prompt.
    
    Args:
        prompt (str): The search query for finding relevant images
        output_path (str): Path to save the downloaded image
    """
    load_dotenv()
    access_key = os.getenv("UNSPLASH_ACCESS_KEY")
    
    if not access_key:
        raise EnvironmentError("UNSPLASH_ACCESS_KEY not found in environment variables")
    
    # Unsplash API endpoint for search
    search_url = "https://api.unsplash.com/search/photos"
    
    headers = {
        "Authorization": f"Client-ID {access_key}"
    }
    
    params = {
        "query": prompt,
        "per_page": 1,  # Get the best match
        "orientation": "landscape"
    }
    
    try:
        print(f"Searching Unsplash for: {prompt}")
        response = requests.get(search_url, headers=headers, params=params, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        
        if "results" in data and len(data["results"]) > 0:
            # Get the first (best) result
            photo = data["results"][0]
            photo_url = photo["urls"]["regular"]  # Medium size image
            
            # Download the image
            print(f"Downloading image: {photo['alt_description'] or 'No description'}")
            image_response = requests.get(photo_url, timeout=30)
            image_response.raise_for_status()
            
            # Save the image
            with open(output_path, "wb") as f:
                f.write(image_response.content)
            
            print(f"\u2713 Unsplash image downloaded and saved to: {output_path}")
            print(f"  Photo by: {photo['user']['name']} on Unsplash")
        else:
            raise RuntimeError("No images found on Unsplash for the given prompt")
            
    except requests.exceptions.RequestException as e:
        if "quota" in str(e).lower() or "limit" in str(e).lower():
            raise RuntimeError("Unsplash API quota or rate limit exceeded")
        raise RuntimeError(f"Unsplash API request failed: {str(e)}")
    except Exception as e:
        raise RuntimeError(f"Failed to download Unsplash image: {str(e)}") 