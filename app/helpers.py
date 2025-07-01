"""
Helper functions for the video production pipeline.
"""

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