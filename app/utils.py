"""
Utility functions for the video production pipeline.
"""

import logging
import re
from pathlib import Path
from typing import Dict, Any, Callable, List
import importlib.util
import sys

def setup_logging(level: str = "INFO") -> logging.Logger:
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('pipeline.log')
        ]
    )
    return logging.getLogger(__name__)

def sanitize_filename(text: str) -> str:
    safe = re.sub(r'[<>:"/\\|?*]', '', text)
    safe = re.sub(r'[^\w\-_.]', '_', safe)
    safe = re.sub(r'_+', '_', safe)
    safe = safe.strip('_')
    return safe or "untitled"

def create_numbered_directory(base_dir: str, name: str) -> Path:
    base_path = Path(base_dir)
    base_path.mkdir(exist_ok=True)
    counter = 1
    while True:
        numbered_dir = base_path / f"{counter:02d}_{name}"
        if not numbered_dir.exists():
            numbered_dir.mkdir(parents=True, exist_ok=True)
            return numbered_dir
        counter += 1

def save_json(data: Any, file_path: Path) -> None:
    """Save a dict or list as JSON to the given file path."""
    import json
    try:
        file_path.parent.mkdir(parents=True, exist_ok=True)
        with open(file_path, 'w') as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        raise RuntimeError(f"Failed to save JSON to {file_path}: {e}")

def load_json(file_path: Path) -> Dict[str, Any]:
    import json
    try:
        with open(file_path, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        raise FileNotFoundError(f"File not found: {file_path}")
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in {file_path}: {e}")
    except Exception as e:
        raise RuntimeError(f"Failed to load JSON from {file_path}: {e}")

def ensure_directory(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path

def get_file_size_mb(file_path: Path) -> float:
    try:
        return file_path.stat().st_size / (1024 * 1024)
    except OSError:
        return 0.0

def format_duration(seconds: float) -> str:
    if seconds < 60:
        return f"{seconds:.1f}s"
    elif seconds < 3600:
        minutes = int(seconds // 60)
        secs = seconds % 60
        return f"{minutes}m {secs:.1f}s"
    else:
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = seconds % 60
        return f"{hours}h {minutes}m {secs:.1f}s"

def validate_file_exists(file_path: Path, description: str = "File") -> None:
    if not file_path.exists():
        raise FileNotFoundError(f"{description} not found: {file_path}")

def clean_temp_files(temp_dir: Path) -> None:
    import shutil
    try:
        if temp_dir.exists():
            shutil.rmtree(temp_dir)
    except Exception as e:
        logging.warning(f"Failed to clean temp directory {temp_dir}: {e}")

def discover_plugins(directory: Path, function_prefix: str) -> dict:
    plugins = {}
    for py_file in directory.glob('*.py'):
        if py_file.name == '__init__.py':
            continue
        module_name = py_file.stem
        spec = importlib.util.spec_from_file_location(module_name, py_file)
        if not spec or not spec.loader:
            continue
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        try:
            spec.loader.exec_module(module)
        except Exception as e:
            logging.warning(f"Failed to import plugin {module_name}: {e}")
            continue
        for attr in dir(module):
            if attr.startswith(function_prefix):
                func = getattr(module, attr)
                if callable(func):
                    engine_name = module_name.replace('tts_', '').replace('generate_', '')
                    plugins[engine_name] = func
    return plugins 