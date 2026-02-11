# OIT Now 2 - Development Guide

This file guides Claude through the project. Reference this for all development work.

## Code Quality Rules

### 1. Comments
- **Do NOT add unnecessary comments**
- Comments explain **WHY**, never **WHAT**
- If code is self-explanatory, no comment needed
- Only add comments when the reasoning behind a decision isn't obvious from the code itself

### 2. Documentation Files
Keep these files updated with every code change:

| File | Purpose |
|------|---------|
| `HEADER.md` | Signatures of ALL classes, methods, functions |
| `TESTS.md` | Test signatures, what they test, and why |
| `CLAUDE.md` | This file - project rules and guidance |

### 3. Ask, Don't Assume
- When uncertain about any decision, ASK the user
- Don't underestimate user's technical knowledge
- Better to clarify than to build the wrong thing

### 4. Test Before Commit
- Run `uv run pytest` to verify tests pass
- **Never** run the main application unless explicitly asked

### 5. No Dead Code
- Remove unused functions, imports, and variables
- Don't leave commented-out code in the codebase
- If code isn't called, delete it

### 6. NEVER Modify Test Expected Results
- **DO NOT** modify `tests/testscreenresults.toml` or any test fixture data
- If tests fail due to OCR variability, that's a code problem to fix, not a data problem
- Expected results represent ground truth - the code must match them, not the other way around
- If you think expected results are wrong, ASK the user first

## Project Structure

```
oitnow2/
├── CLAUDE.md           # This file - development rules
├── HEADER.md           # Class/method signatures
├── TESTS.md            # Test documentation
├── pyproject.toml      # UV/Python project config
├── convert.py          # CLI tool for hand history de-anonymization
├── e2e_test.py         # E2E test script for manual validation
├── image_analyzer/     # Main OCR package (uses Claude Haiku API)
│   ├── __init__.py     # Public API exports
│   ├── analyzer.py     # analyze_image, analyze_screenshot, extract_hand_number
│   ├── constants.py    # Regions, detection pixels, few-shot examples
│   ├── models/
│   │   ├── __init__.py
│   │   ├── PlayerRegion.py
│   │   └── ScreenshotFilename.py
│   └── llm/
│       ├── __init__.py      # get_provider factory
│       ├── protocol.py      # LLMProvider Protocol
│       └── anthropic.py     # Claude Haiku implementation
├── hand_history/       # Hand history de-anonymizer
│   ├── __init__.py     # Public API, seat mapping
│   ├── parser.py       # HandHistory dataclass, parse functions
│   ├── converter.py    # ConversionResult, convert functions
│   └── seat_mapping.toml  # Configurable position -> seat mapping
├── settings/           # Configuration
│   ├── __init__.py     # Public API exports
│   └── config.py       # Settings load/save
├── temp/               # Scratch files, large data (gitignored)
└── tests/
    ├── __init__.py
    ├── test_image_analyzer.py
    ├── test_hand_history.py
    ├── test_settings.py
    ├── testscreenresults.toml  # DO NOT MODIFY
    ├── images/         # Test screenshots (testscreen1-7.png)
    └── fixtures/       # Integration test fixtures
```

## Architecture Principles

1. **Protocols first** - Define contracts before implementations
2. **Test everything** - Every component gets unit tests
3. **Single responsibility** - Each function does one thing well
4. **Dependency injection** - Pass dependencies, don't hardcode globals
5. **Immutable data** - Use dataclasses with frozen=True for data structures

## Commands

```bash
# Run tests
uv run pytest

# Run tests with coverage
uv run pytest --cov=image_analyzer

# Run specific test
uv run pytest tests/test_image_analyzer.py::test_function_name

# Run hand history converter
uv run python convert.py --hands input/hands --screenshots input/screenshots --output output/
```

## Module Overview

### image_analyzer (package)
Extracts player names from GGPoker/Natural8 table screenshots using Claude Haiku API.

**Public API:**
- `analyze_screenshot()` - Analyze image file, returns dict of position -> player name
- `analyze_image()` - Analyze numpy array image
- `analyze_screenshots_batch()` - Analyze multiple screenshots in one API call
- `extract_hand_number()` - Extract hand number from screenshot
- `detect_table_type()` - Auto-detect GGPoker vs Natural8 table
- `PlayerRegion` - Dataclass for region definition
- `ScreenshotFilename` - Parser for GGPoker screenshot filenames
- `DEFAULT_REGIONS` - Standard 6-max table regions

### hand_history (package)
De-anonymizes GGPoker hand histories by replacing encrypted player IDs with real names from screenshots.

**Public API:**
- `parse_file()` - Parse hand history file into HandHistory objects
- `convert_hands()` - Convert hands using screenshot OCR data
- `position_to_seat()` - Map screenshot positions to seat numbers
- `HandHistory` - Dataclass for parsed hand data
- `ConversionResult` - Dataclass for conversion results
