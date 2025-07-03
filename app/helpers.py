"""
Helper functions for the video production pipeline.
"""

import os
import requests

def build_prompt(input_data):
    """Build a prompt string for the script generation step from input data, with explicit instructions for structured output."""
    topic = input_data.get("topic", "")
    keywords = input_data.get("keywords", [])
    prompt = input_data.get("prompt", "")
    lines = [
        "You are an expert children's scriptwriter.",
        "Write a fun, educational script for a video on the following topic, split into clear sections.",
        "Return the result as a JSON array, where each item has these fields: heading (string), narration (string), and duration (number, estimated seconds).",
        "Do NOT include markdown, code blocks, or image prompts in the narration.",
        "Example output:",
        '[',
        '  {',
        '    "heading": "Section Title",',
        '    "narration": "A concise, engaging narration for this section.",',
        '    "duration": 12',
        '  },',
        '  ...',
        ']',
        "---",
    ]
    if topic:
        lines.append(f"Topic: {topic}")
    if keywords:
        lines.append(f"Keywords: {', '.join(keywords)}")
    if prompt:
        lines.append(f"Prompt: {prompt}")
    return "\n".join(lines)

def estimate_duration(text):
    """Estimate duration in seconds for a given narration text."""
    words = text.split()
    words_per_minute = 140  # average speaking rate
    minutes = len(words) / words_per_minute
    return max(2, round(minutes * 60, 2))  # at least 2 seconds

def create_prompt_from_section(section, topic, keywords):
    """Create an image prompt from a section, topic, and keywords."""
    heading = section.get('heading', '')
    narration = section.get('narration', '')
    prompt_parts = [heading, narration, topic]
    if keywords:
        prompt_parts.append(", ".join(keywords))
    return ". ".join([p for p in prompt_parts if p]).strip()

def ensure_section_consistency(sections, min_sections=2):
    """Ensure sections is a list of well-formed sections. Raise ValueError if not, or attempt to split/merge if possible."""
    # Remove empty or malformed sections
    valid_sections = [s for s in sections if isinstance(s, dict) and s.get('heading') and s.get('narration')]
    if len(valid_sections) >= min_sections:
        return valid_sections
    # Attempt to split a single long section by headings in narration (very basic)
    if len(valid_sections) == 1:
        narration = valid_sections[0]['narration']
        # Split on double newlines or numbered headings
        import re
        parts = re.split(r'\n\n|\n\d+\. ', narration)
        if len(parts) > 1:
            return [
                {
                    'heading': f'Section {i+1}',
                    'narration': part.strip(),
                    'duration': estimate_duration(part.strip())
                }
                for i, part in enumerate(parts) if part.strip()
            ]
    raise ValueError("Script must have at least two well-formed sections.")

def enrich_metadata(meta, input_data=None):
    """Ensure all recommended metadata fields are present, using input_data or defaults if needed."""
    import datetime
    enriched = dict(meta) if meta else {}
    enriched.setdefault('language', 'en')
    enriched.setdefault('target_age', input_data.get('target_age', 'children') if input_data else 'children')
    enriched.setdefault('tags', input_data.get('keywords', []) if input_data else [])
    enriched.setdefault('estimated_reading_level', 'unknown')
    enriched.setdefault('created_by', 'auto-pipeline')
    enriched.setdefault('model', input_data.get('model', 'unknown') if input_data else 'unknown')
    enriched.setdefault('generated_at', datetime.datetime.now().isoformat())
    return enriched

def export_srt(sections, srt_path):
    """Export sections to SRT file. Assumes each section has 'heading', 'narration', and 'duration'."""
    def seconds_to_timestamp(seconds):
        h = int(seconds // 3600)
        m = int((seconds % 3600) // 60)
        s = int(seconds % 60)
        ms = int((seconds - int(seconds)) * 1000)
        return f"{h:02}:{m:02}:{s:02},{ms:03}"
    lines = []
    current_time = 0.0
    for idx, section in enumerate(sections, 1):
        start = seconds_to_timestamp(current_time)
        end = seconds_to_timestamp(current_time + float(section.get('duration', 2)))
        lines.append(f"{idx}\n{start} --> {end}\n[{section.get('heading', '')}]\n{section.get('narration', '').strip()}\n")
        current_time += float(section.get('duration', 2))
    with open(srt_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))

def download_image_from_unsplash(prompt, output_path):
    """Download the first Unsplash image for the prompt to output_path."""
    api_key = os.getenv("UNSPLASH_API_KEY") or os.getenv("UNSPLASH_ACCESS_KEY")
    if not api_key:
        raise RuntimeError("UNSPLASH_API_KEY or UNSPLASH_ACCESS_KEY not set in environment.")
    headers = {"Authorization": f"Client-ID {api_key}"}
    params = {"query": prompt, "per_page": 1, "orientation": "landscape"}
    resp = requests.get("https://api.unsplash.com/search/photos", params=params, headers=headers)
    resp.raise_for_status()
    data = resp.json()
    if data["results"]:
        img_url = data["results"][0]["urls"]["regular"]
        img_data = requests.get(img_url).content
        with open(output_path, "wb") as f:
            f.write(img_data)
    else:
        raise RuntimeError(f"No Unsplash image found for prompt: {prompt}")

def get_image_url_from_ai(prompt, model_name=None):
    """
    Use Gemini to find a relevant image URL for the given prompt.
    Returns a direct image URL (jpg/png/etc) or raises if not found.
    """
    from google.generativeai.client import configure
    from google.generativeai.generative_models import GenerativeModel
    import os
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY not found in environment.")
    configure(api_key=api_key)
    model_name = model_name or "models/gemini-1.5-flash"
    model = GenerativeModel(model_name)
    # Prompt Gemini to return a direct image URL only
    ai_prompt = (
        f"Find a single, high-quality, copyright-free image for this topic: '{prompt}'. "
        "Return ONLY the direct image URL (ending in .jpg, .jpeg, .png, or .webp). "
        "Do not include any explanation, markdown, or text."
    )
    response = model.generate_content(ai_prompt)
    url = response.text.strip().split()[0]
    # Basic validation
    if not (url.startswith("http") and any(url.lower().endswith(ext) for ext in [".jpg", ".jpeg", ".png", ".webp"])):
        raise RuntimeError(f"AI did not return a valid image URL: {url}")
    return url

def download_image_from_url(url, output_path):
    """Download an image from a direct URL to output_path."""
    import requests
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    with open(output_path, "wb") as f:
        f.write(resp.content) 