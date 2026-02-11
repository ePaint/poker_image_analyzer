# Last State - Continue From Here

## Current Status

**Application is fully functional** with GUI and packaging support.

## What's Complete

### Core Backend
- `image_analyzer/` - OCR using Claude Haiku API with few-shot learning
- `hand_history/` - Parsing, conversion, seat mapping with TableType Literal
- `image_analyzer/ocr_dump/` - Versioned OCR dump format (v1, v2)
- `settings/` - Cross-platform settings storage
- `convert.py` - CLI tool for batch processing

### GUI (PySide6)
- `gui/app.py` - Entry point with dark theme
- `gui/main_window.py` - Main window with drag-drop zones
- `gui/drop_zone.py` - Drag-and-drop widget (folder or file mode)
- `gui/file_list.py` - File preview with validation
- `gui/workers.py` - Background workers with rate limiting
- `gui/settings_dialog.py` - API key, seat mapping, corrections

### Packaging
- `HandHistoryDeanonymizer.spec` - PyInstaller spec (macOS .app + Windows .exe)
- `installer.iss` - Inno Setup script for Windows installer
- `app.py` - Entry point for PyInstaller

### Tests
- 105 tests passing
- Unit tests for all modules
- Integration tests with real OCR dump fixtures (v1 and v2)

## Project Structure

```
oitnow2/
├── app.py                      # PyInstaller entry point
├── convert.py                  # CLI tool
├── HandHistoryDeanonymizer.spec # PyInstaller config
├── installer.iss               # Inno Setup (Windows)
├── gui/
│   ├── app.py                  # QApplication, dark theme
│   ├── main_window.py          # Main UI
│   ├── drop_zone.py            # Drag-drop widget
│   ├── file_list.py            # File list with refresh
│   ├── workers.py              # ScreenshotWorker, ConversionWorker
│   └── settings_dialog.py      # Settings tabs
├── image_analyzer/
│   ├── analyzer.py             # analyze_screenshot, detect_table_type
│   ├── constants.py            # Regions, few-shot examples
│   ├── models/                 # PlayerRegion, ScreenshotFilename
│   ├── llm/                    # AnthropicProvider
│   └── ocr_dump/               # v1/v2 format writers and parsers
├── hand_history/
│   ├── parser.py               # HandHistory dataclass
│   ├── converter.py            # ConversionResult, convert_hands
│   └── seat_mapping.toml       # Position -> seat config
├── settings/
│   └── config.py               # Cross-platform settings paths
└── tests/
    ├── test_gui.py
    ├── test_hand_history.py
    ├── test_image_analyzer.py
    ├── test_settings.py
    └── fixtures/integration/   # v1/v2 OCR dumps, sample hands
```

## Key Type Aliases

```python
TableType = Literal["ggpoker", "natural8"]      # hand_history/__init__.py
OcrDumpVersion = Literal["v1", "v2"]            # image_analyzer/ocr_dump/__init__.py
ProviderName = Literal["anthropic"]             # image_analyzer/llm/__init__.py
```

## Commands

```bash
# Development
uv run pytest                              # Run all tests
uv run ruff check .                        # Linting
uv tool run ty check                       # Type checking
uv run python app.py                       # Launch GUI

# Packaging (macOS)
uv run pyinstaller HandHistoryDeanonymizer.spec --noconfirm
open "dist/Hand History De-anonymizer.app"

# Packaging (Windows) - run on Windows machine
pyinstaller HandHistoryDeanonymizer.spec --noconfirm
# Then run Inno Setup with installer.iss
```

## Settings Paths

| Platform | Location |
|----------|----------|
| macOS | `~/Library/Application Support/HandHistoryDeanonymizer/` |
| Windows | `%APPDATA%\HandHistoryDeanonymizer\` |
| Linux | `~/.config/handhistorydeanonymizer/` |
| Development | `./settings.toml` (if exists, takes priority) |

## Next Steps (If Continuing)

1. **GitHub Actions** - Auto-build for macOS and Windows on push/release
2. **App icon** - Create `.icns` (macOS) and `.ico` (Windows)
3. **Code signing** - Sign macOS app and Windows exe for distribution
4. **Auto-updater** - Check for updates on launch
