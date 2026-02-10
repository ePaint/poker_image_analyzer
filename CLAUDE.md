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
├── image_analyzer/     # Main OCR package
│   ├── __init__.py     # Public API exports
│   ├── analyzer.py     # analyze_image, analyze_screenshot
│   ├── bin/            # External binaries (gitignored)
│   │   └── tesseract/  # Tesseract OCR installation
│   ├── models/
│   │   ├── __init__.py
│   │   ├── PlayerRegion.py
│   │   └── OCRResult.py
│   ├── engines/
│   │   ├── __init__.py
│   │   ├── protocol.py      # OCREngine Protocol
│   │   └── easyocr_engine.py
│   └── upscalers/
│       ├── __init__.py
│       └── clahe.py
├── settings/           # Configuration and engine management
│   ├── __init__.py     # Public API exports
│   ├── config.py       # Settings load/save, get_engine factory
│   ├── engine_manager.py  # Async engine availability/install API
│   ├── models/
│   │   ├── __init__.py
│   │   └── EngineName.py  # EngineName enum
│   └── installers/
│       ├── __init__.py
│       ├── protocol.py    # EngineInstaller Protocol
│       ├── easyocr.py     # EasyOCR installer
│       └── tesseract.py   # Tesseract installer
├── temp/               # Downloaded installers (gitignored)
└── tests/
    ├── __init__.py
    ├── test_image_analyzer.py
    ├── test_settings.py
    ├── test_engine_manager.py
    ├── test_installers.py
    ├── testscreenresults.toml  # DO NOT MODIFY
    └── images/         # Test screenshots
```

## Architecture Principles

1. **Protocols first** - Define contracts before implementations
2. **Test everything** - Every component gets unit tests
3. **Single responsibility** - Each function does one thing well
4. **Dependency injection** - Pass dependencies, don't hardcode globals
5. **Immutable data** - Use dataclasses with frozen=True for data structures

## Commands

**IMPORTANT:** Always `cd` to the project directory before running `uv run` commands:

```bash
# Run tests
cd D:\MEDIA\DOCUMENTOS\ThatExcelGuy\TEG_Python\oitnow2 && uv run pytest

# Run tests with coverage
cd D:\MEDIA\DOCUMENTOS\ThatExcelGuy\TEG_Python\oitnow2 && uv run pytest --cov=image_analyzer

# Run specific test
cd D:\MEDIA\DOCUMENTOS\ThatExcelGuy\TEG_Python\oitnow2 && uv run pytest tests/test_image_analyzer.py::test_function_name

# Run standalone scripts (PYTHONPATH=. required for local imports)
cd D:\MEDIA\DOCUMENTOS\ThatExcelGuy\TEG_Python\oitnow2 && PYTHONPATH=. uv run python tests/test_combinations_report.py
```

## Module Overview

### image_analyzer (package)
Extracts player names from GGPoker 6-max PLO-5 table screenshots using pluggable OCR engines.

**Public API:**
- `analyze_screenshot()` - Analyze image file, returns dict of position -> player name
- `analyze_image()` - Analyze numpy array image
- `PlayerRegion` - Dataclass for region definition
- `OCRResult` - Dataclass for OCR detection results
- `EasyOCREngine` - Default OCR engine implementation
- `OCREngine` - Protocol for custom OCR engines
- `DEFAULT_REGIONS` - Standard 6-max table regions
