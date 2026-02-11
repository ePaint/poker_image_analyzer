# Hand History De-anonymizer

De-anonymize GGPoker/Natural8 hand histories by extracting real player names from table screenshots.

## Features

- **OCR via Claude Haiku API** - Extracts player names from table screenshots
- **Batch processing** - Process multiple screenshots and hand histories at once
- **GUI application** - Drag-and-drop interface for easy use
- **CLI tool** - Command-line interface for automation
- **OCR dump files** - Save/load OCR results to avoid re-processing

## Installation

Download the latest installer from [Releases](../../releases).

Or run from source:

```bash
# Install dependencies
uv sync

# Run GUI
uv run python app.py

# Run CLI
uv run python convert.py --hands input/hands --screenshots input/screenshots --output output/
```

## Usage

1. Set your Anthropic API key in **File → Settings**
2. Drop a folder of screenshots (or an existing OCR dump file)
3. Drop a folder of hand history files
4. Select an output folder
5. Click **Convert**

## Requirements

- Windows 10/11 or macOS 10.15+
- Anthropic API key (for OCR processing)

## Building

```bash
# Build installer (bumps version automatically)
uv run python build.py

# Build without version bump
uv run python build.py --no-bump
```

## License

Private - All rights reserved.
