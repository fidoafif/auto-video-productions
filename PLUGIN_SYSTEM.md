# Plugin System for Dynamic Engine Loading

## Overview

This project supports a **plugin system** for both TTS (Text-to-Speech) and image generation engines. New engines can be added simply by dropping a Python file into the appropriate directory—**no changes to the core code are required**.

The system will automatically discover, import, and register any compatible engine modules at runtime.

---

## How It Works

- **Discovery**: At startup, the pipeline scans the `tts_engines/` and `image_engines/` directories for `.py` files (excluding `__init__.py`).
- **Import**: Each file is imported as a module.
- **Registration**: Any function in the module that matches the expected naming convention is registered as an available engine.
- **Usage**: The engine can be selected in your `input.json` by name.

---

## Directory Structure

```
app/
├── tts_engines/
│   ├── tts_gemini.py
│   ├── tts_espeak.py
│   └── ...
├── image_engines/
│   ├── dalle.py
│   ├── stable_diffusion.py
│   └── ...
```

---

## Naming Conventions

### TTS Engines
- File: `tts_engines/tts_<engine_name>.py`
- Function: `def tts_<engine_name>(text, output_path, model=None, voice=None): ...`

### Image Engines
- File: `image_engines/generate_<engine_name>_image.py` **or** `image_engines/<engine_name>.py`
- Function: `def generate_<engine_name>_image(prompt, output_path, model=None, size=None, quality=None): ...`
  - The loader will accept any function starting with `generate_`.

---

## How to Add a New Engine Plugin

### 1. **Create the Engine File**
- For TTS: Place your file in `tts_engines/` and name it `tts_<engine_name>.py`.
- For Image: Place your file in `image_engines/` and name it `generate_<engine_name>_image.py` or `<engine_name>.py`.

### 2. **Define the Engine Function**
- For TTS:
    ```python
    def tts_myengine(text, output_path, model=None, voice=None):
        # Your implementation here
        pass
    ```
- For Image:
    ```python
    def generate_myengine_image(prompt, output_path, model=None, size=None, quality=None):
        # Your implementation here
        pass
    ```

### 3. **(Optional) Add Metadata**
You can add variables like `PLUGIN_NAME`, `PLUGIN_DESCRIPTION`, etc., to your module for future use or display.

### 4. **Test Your Plugin**
- Set the engine in your `input.json`:
    - For TTS: `"engine": "myengine"`
    - For Image: `"engine": "myengine"`
- Run the pipeline. Your engine will be auto-discovered and used.

---

## Example: Adding a Dummy TTS Engine

**File:** `tts_engines/tts_dummy.py`
```python
def tts_dummy(text, output_path, model=None, voice=None):
    with open(output_path, 'w') as f:
        f.write(f"[DUMMY AUDIO for: {text}]")
```

**Set in input.json:**
```json
"tts": {
    "engine": "dummy"
}
```

---

## Troubleshooting

- **Plugin not found?**
    - Make sure your file and function follow the naming conventions.
    - Check the logs for import errors or warnings.
- **Function signature mismatch?**
    - Your function should accept all required parameters, even if you don't use them.
- **Engine not available?**
    - The engine name in `input.json` must match the plugin's filename (minus prefix/suffix).

---

## Best Practices
- Keep each engine in its own file.
- Use clear, unique names for your engines.
- Document your engine's requirements and usage in the module docstring.
- Handle errors gracefully in your plugin code.

---

## Advanced: Plugin Metadata (Optional)
You can add metadata to your plugin module for display or selection in a UI:
```python
PLUGIN_NAME = "My Engine"
PLUGIN_DESCRIPTION = "A demo TTS engine for testing."
PLUGIN_VERSION = "1.0.0"
```

---

## Summary
- **No core code changes needed to add new engines!**
- Just drop in a new `.py` file with the right function.
- The system will auto-discover and use it.

If you have questions or want to extend the plugin system further (e.g., for hot-reloading, plugin config, or UI integration), just ask! 