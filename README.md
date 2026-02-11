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

## Input Requirements

### Screenshots

Screenshots must be **GGPoker/Natural8 table screenshots** with filenames in this exact format:

```
YYYY-MM-DD_ HH-MM_AM/PM_$SB_$BB_#TABLEID.png
```

**Examples of valid filenames:**
- `2024-02-08_ 09-39_AM_$2_$5_#154753304.png`
- `2024-12-21_ 03-15_PM_$0.50_$1_#262668465.png`
- `2025-01-15_ 11-30_AM_$5_$10_#123456789.png`

**Format breakdown:**

| Part | Example | Description |
| ---- | ------- | ----------- |
| Date | `2024-02-08` | Year-Month-Day |
| Space + Underscore | `_ ` | Literal space after underscore |
| Time | `09-39` | Hour-Minute (12-hour format) |
| Period | `AM` or `PM` | Morning or afternoon |
| Small blind | `$2` or `$0.50` | With dollar sign |
| Big blind | `$5` or `$1` | With dollar sign |
| Table ID | `#154753304` | Hash followed by digits |
| Extension | `.png` | Must be PNG |

**Important:** GGPoker automatically names screenshots in this format when you press the screenshot hotkey. Don't rename the files.

### Hand History Files

- Standard GGPoker/Natural8 `.txt` hand history export files
- The hand numbers in the files must match the table IDs in the screenshot filenames

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
