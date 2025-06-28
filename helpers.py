"""
Helper functions for the Automated Video Production Pipeline.
"""
import re

def build_prompt(input_data):
    """Builds the prompt for script generation based on input data."""
    topic = input_data.get("topic", "")
    keywords = input_data.get("keywords", [])
    prompt = input_data.get("prompt", "")
    duration = input_data.get("duration")
    kw_str = f"\nKeywords: {', '.join(keywords)}" if keywords else ""
    duration_str = f" for a {duration}-minute video" if duration else ""
    if duration and f"{duration}-minute" not in prompt:
        prompt = f"Write a video script{duration_str}. " + prompt.lstrip("Write a video script. ")
    output_instructions = (
        " Structure the script as an array of sections, each with a short heading, a narration, and an estimated duration in seconds for that section. "
        "Do NOT include visual cues, markdown, or formatting—just plain text. "
        "Output only the narration for each section. The output should be easy to convert to voice narration, with each section's narration as a single string. "
        "Do not include any visual instructions, only headings, narration, and duration. Output is in JSON format."
    )
    return f"Topic: {topic}{kw_str}\n{prompt}{output_instructions}"

def estimate_duration(narration, wpm=140):
    """Estimates the duration in seconds for a narration string, given words per minute."""
    words = len(narration.split())
    return int((words / wpm) * 60)

def safe_folder_name(name):
    """Sanitizes a string to be safe for use as a folder name."""
    return re.sub(r'[^\w\-_ ]', '', name).replace(' ', '_')

def create_prompt_from_section(section, topic, keywords):
    """Creates an image generation prompt from a script section."""
    heading = section.get('heading', '')
    narration = section.get('narration', '')
    prompt = f"Create a colorful, child-friendly illustration for: {heading}. "
    prompt += f"Scene: {narration[:200]}... "
    prompt += f"Style: Bright, cheerful, cartoon-like, suitable for children. "
    prompt += f"Topic: {topic}. "
    prompt += f"Keywords: {', '.join(keywords)}. "
    prompt += "No text, no words, just visual elements."
    return prompt 