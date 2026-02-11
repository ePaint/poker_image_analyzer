# Last State - Continue From Here

## Current Task

Implement PySide6 GUI for the Hand History De-anonymizer tool.

## What's Done

1. **Backend is complete:**
   - `image_analyzer/` - OCR using Claude Haiku API
   - `hand_history/` - Parsing and conversion logic
   - `convert.py` - Working CLI tool
   - All 72 tests pass

## Plan Summary

Create a `gui/` package with PySide6:

```
gui/
├── __init__.py        # Package exports
├── app.py             # QApplication entry point, dark theme
├── main_window.py     # Main window with drag-drop zones
├── settings_dialog.py # Modal dialog for API key configuration
├── file_list.py       # QListWidget subclass for file preview
├── workers.py         # QThread workers for background processing
└── drop_zone.py       # Drag-and-drop widget for folders
```

**Key decisions:**
- PySide6 (LGPL license, same API as PyQt6)
- Dark theme (follows system preference, with manual override)
- Drag-and-drop folder input + Browse buttons as fallback
- File list preview before processing
- Settings dialog for API key (separate from main window)
- QThread workers for API calls (non-blocking UI)
- Cancel button support
- pytest-qt for widget testing

## Files to Create/Modify

| File | Action |
|------|--------|
| `gui/__init__.py` | Create - package exports |
| `gui/app.py` | Create - entry point, dark theme setup |
| `gui/main_window.py` | Create - main UI with drop zones |
| `gui/settings_dialog.py` | Create - API key dialog |
| `gui/file_list.py` | Create - file preview list widget |
| `gui/drop_zone.py` | Create - drag-and-drop widget |
| `gui/workers.py` | Create - ScreenshotWorker, ConversionWorker |
| `pyproject.toml` | Modify - add PySide6>=6.6.0, pytest-qt |
| `tests/test_gui.py` | Create - worker and widget tests |

## UI Layout

```
+----------------------------------------------------------+
| File  Settings  Help                                     |
+----------------------------------------------------------+
| +------------------------+  +------------------------+   |
| |   Drop Screenshots     |  |     Drop Hand Files    |   |
| |        Folder          |  |        Folder          |   |
| |    (or click Browse)   |  |    (or click Browse)   |   |
| +------------------------+  +------------------------+   |
|                                                          |
| Screenshots (12 files)       Hand Files (3 files)        |
| +------------------------+  +------------------------+   |
| | GGPoker_2024-02-08... |  | HH20240208_OM26266... |   |
| | GGPoker_2024-02-08... |  | HH20240209_OM26267... |   |
| | GGPoker_2024-02-08... |  | HH20240210_OM26268... |   |
| +------------------------+  +------------------------+   |
|                                                          |
| Output: [________________________] [Browse...]           |
+----------------------------------------------------------+
| Progress                                                 |
| [====================            ] 60%                   |
| Processing screenshot 6/12: GGPoker_2024-02-08...        |
+----------------------------------------------------------+
| Log                                                      |
| Hand #OM262668465: 5 players matched                     |
| Hand #OM262668466: 6 players matched                     |
+----------------------------------------------------------+
|                            [Convert]  [Cancel]           |
+----------------------------------------------------------+
```

**Settings Dialog (File > Settings or Ctrl+,):**
```
+----------------------------------+
| Settings                    [X]  |
+----------------------------------+
| Anthropic API Key:               |
| [****************************]   |
| [Show] [Test Connection]         |
|                                  |
| [ ] Dark theme (follows system)  |
|                                  |
|              [Save]  [Cancel]    |
+----------------------------------+
```

## Backend API to Use

```python
# From image_analyzer
analyze_screenshot(image_path, api_key=None) -> dict[str, str]
extract_hand_number_from_file(image_path, api_key=None) -> str | None
ScreenshotFilename.is_valid(filename) -> bool

# From hand_history
parse_file(path) -> list[HandHistory]
convert_hands(hands, hand_number_to_seats) -> list[ConversionResult]
write_converted_file(results, output_path)
write_skipped_file(results, output_path)
position_to_seat(position_names, seat_mapping) -> dict[int, str]
load_seat_mapping() -> dict[str, int]
```

## Test Strategy

**pytest-qt tests (tests/test_gui.py):**
- `test_screenshot_worker_emits_progress` - Worker signals progress correctly
- `test_screenshot_worker_cancellation` - Cancel stops processing
- `test_conversion_worker_emits_results` - Worker returns ConversionResult
- `test_drop_zone_accepts_folders` - Drag-drop accepts directory mimetypes
- `test_drop_zone_rejects_files` - Drag-drop rejects individual files
- `test_file_list_updates_on_folder_change` - List populates when folder set
- `test_settings_dialog_saves_api_key` - API key persists to .env
- `test_settings_dialog_masks_api_key` - Password field hides text
- `test_convert_button_disabled_without_inputs` - Validation works
- `test_convert_button_enabled_with_valid_inputs` - Validation works

## Next Steps

1. Add PySide6 and pytest-qt to pyproject.toml
2. Run `uv sync` to install dependencies
3. Create gui/ package files
4. Create tests/test_gui.py
5. Run `uv run pytest` to verify all tests pass
6. Test manually with `uv run python -m gui.app`
7. Update HEADER.md and TESTS.md

## Commands

```bash
uv run pytest                  # Run all tests
uv sync                        # Install deps after adding PySide6
uv run python -m gui.app       # Launch GUI (after implementation)
```
