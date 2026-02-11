# Test Documentation

## tests/test_settings.py

### TestLoadSettings

| Test | Purpose |
|------|---------|
| `test_returns_dict` | Verifies load_settings returns a dict |
| `test_returns_defaults_when_file_missing` | Returns DEFAULT_SETTINGS when file doesn't exist |
| `test_loads_custom_values_from_file` | Loads custom settings from TOML file |

### TestSaveSettings

| Test | Purpose |
|------|---------|
| `test_creates_file` | Verifies save_settings creates the TOML file |
| `test_overwrites_existing_file` | Confirms save overwrites previous content |
| `test_roundtrip_preserves_data` | Save then load returns identical data |

### TestDefaultSettings

| Test | Purpose |
|------|---------|
| `test_default_settings_has_folder_keys` | Verifies DEFAULT_SETTINGS contains folder persistence keys |

## tests/test_image_analyzer.py

### TestPlayerRegion

| Test | Purpose |
|------|---------|
| `test_is_immutable` | Verifies PlayerRegion cannot be modified after creation |
| `test_stores_values` | Verifies all fields are stored correctly |

### TestScreenshotFilename

| Test | Purpose |
|------|---------|
| `test_parse_valid_filename` | Parses standard GGPoker filename with integer stakes |
| `test_parse_pm_filename` | Parses PM timestamps correctly |
| `test_parse_from_path` | Parses Path objects (extracts name) |
| `test_parse_invalid_returns_none` | Returns None for non-GGPoker filenames |
| `test_is_valid` | Static method returns bool for pattern match |
| `test_stakes_property` | Formats stakes as "$SB/$BB" string |
| `test_datetime_property_am` | Parses AM timestamps to datetime |
| `test_datetime_property_pm` | Parses PM timestamps to datetime (24h conversion) |
| `test_is_immutable` | Verifies dataclass is frozen |
| `test_parse_decimal_stakes` | Parses filenames with decimal small blind (e.g., $0.50/$1) |
| `test_parse_decimal_both_blinds` | Parses filenames where both blinds are decimal (e.g., $0.25/$0.50) |

### TestDefaultRegions

| Test | Purpose |
|------|---------|
| `test_has_six_regions` | Confirms 6-max table coverage |
| `test_region_names` | Verifies all position names exist |

### TestIntegration

| Test | Purpose |
|------|---------|
| `test_analyze_screenshot_file_not_found` | FileNotFoundError for missing files |
| `test_analyze_returns_all_positions` | All 6 positions returned in results dict (mocked Anthropic) |
| `test_analyze_matches_expected` | Mocked Anthropic returns match expected results (parametrized per image) |

## Fixtures

| Fixture | Scope | Purpose |
|---------|-------|---------|
| `expected_results` | module | Loads expected results from testscreenresults.toml |

## Test Images

Located in `tests/images/`:
- testscreen1.png through testscreen7.png
- All from GGPoker 6-max PLO-5 tables

## tests/test_hand_history.py

### TestParseHand

| Test | Purpose |
|------|---------|
| `test_parses_hand_number` | Extracts hand number from header line |
| `test_parses_table_name` | Extracts table name from Table line |
| `test_parses_timestamp` | Parses timestamp into datetime object |
| `test_parses_seats` | Extracts seat number to player name mapping |
| `test_stores_raw_text` | Preserves original hand text for replacement |
| `test_returns_none_for_invalid_header` | Returns None for non-hand text |
| `test_returns_none_for_empty_string` | Returns None for empty input |
| `test_returns_none_for_missing_table` | Returns None when Table line missing |

### TestHandHistory

| Test | Purpose |
|------|---------|
| `test_is_immutable` | Verifies HandHistory is frozen dataclass |
| `test_get_player_at_seat` | Helper method returns player at seat or None |
| `test_get_seat_for_player` | Helper method returns seat for player or None |

### TestParseFile

| Test | Purpose |
|------|---------|
| `test_parses_multiple_hands` | Splits file into multiple hands correctly |
| `test_raises_for_missing_file` | FileNotFoundError for nonexistent path |
| `test_handles_empty_file` | Returns empty list for empty file |

### TestFindHandByNumber

| Test | Purpose |
|------|---------|
| `test_finds_existing_hand` | Locates hand by number in list |
| `test_returns_none_for_missing` | Returns None when hand not found |
| `test_handles_empty_list` | Returns None for empty hands list |

### TestConvertHand

| Test | Purpose |
|------|---------|
| `test_replaces_encrypted_ids` | Replaces encrypted IDs with real names |
| `test_preserves_hero` | Does not replace "Hero" player name |
| `test_skips_empty_names` | Does not replace with "EMPTY" |
| `test_tracks_replacements` | Records which IDs were replaced |
| `test_replaces_all_occurrences` | Replaces ID everywhere in hand text |

### TestConvertHands

| Test | Purpose |
|------|---------|
| `test_converts_matching_hands` | Converts hands with matching screenshot data |
| `test_marks_unmatched_as_failed` | Marks hands without screenshot as failed |

### TestWriteFiles

| Test | Purpose |
|------|---------|
| `test_write_converted_file` | Writes successful conversions to file |
| `test_write_converted_skips_failed` | Does not create file for all-failed results |
| `test_write_skipped_file` | Writes failed hands with error messages |

### TestSeatMapping

| Test | Purpose |
|------|---------|
| `test_default_seat_mapping` | Verifies DEFAULT_SEAT_MAPPING values |
| `test_load_seat_mapping_returns_default_for_missing_file` | Uses defaults when config missing |
| `test_load_seat_mapping_from_file` | Loads custom mapping from TOML |
| `test_position_to_seat` | Converts position names to seat numbers |
| `test_position_to_seat_with_custom_mapping` | Uses custom mapping when provided |
| `test_position_to_seat_ignores_unknown_positions` | Skips positions not in mapping |

### TestIntegration (hand_history)

| Test | Purpose |
|------|---------|
| `test_full_conversion_workflow` | End-to-end test: parse, map seats, convert |
| `test_write_converted_and_skipped` | Tests file output for both success and failure cases |

## tests/test_image_analyzer.py (additions)

### TestHandInfoRegion

| Test | Purpose |
|------|---------|
| `test_region_exists` | Verifies HAND_INFO_REGION is defined |
| `test_region_position` | Verifies region coordinates (0, 0, 350, 25) |

### TestExtractHandNumber

| Test | Purpose |
|------|---------|
| `test_file_not_found` | FileNotFoundError for missing files |
| `test_extracts_hand_number` | Extracts OM number from LLM response |
| `test_returns_none_for_no_match` | Returns None when no #OM pattern found |
| `test_extracts_from_longer_text` | Extracts OM number from text with other content |
| `test_extracts_from_raw_response_without_index` | Falls back to raw response when no indexed format (single crop) |

## tests/test_gui.py

### TestDropZone

| Test | Purpose |
|------|---------|
| `test_drop_zone_initial_state` | Verifies drop zone starts with no folder and accepts drops |
| `test_drop_zone_emits_signal_on_folder_set` | Signal emitted when folder is set |
| `test_drop_zone_clear` | Clears folder and resets state |

### TestFileListWidget

| Test | Purpose |
|------|---------|
| `test_file_list_initial_state` | Empty list on initialization |
| `test_file_list_populates_on_set_folder` | Populates with matching files |
| `test_file_list_with_validator` | Validator marks invalid files |
| `test_file_list_refresh_signal` | Refresh button emits signal |
| `test_file_list_refresh_rereads_folder` | Refresh re-reads folder contents |
| `test_file_list_handles_missing_folder` | Handles non-existent folders |

### TestSettingsDialog

| Test | Purpose |
|------|---------|
| `test_settings_dialog_masks_api_key` | API key input uses password mode |
| `test_settings_dialog_toggles_key_visibility` | Show/Hide button toggles echo mode |
| `test_settings_dialog_get_api_key` | Returns trimmed API key |
| `test_settings_dialog_seat_spinboxes_exist` | All 6 position spinboxes exist |
| `test_settings_dialog_reset_seat_mapping` | Reset button restores defaults |
| `test_settings_dialog_add_correction_row` | Add button creates new row |
| `test_settings_dialog_remove_correction_row` | Remove button deletes selected row |

### TestSettingsFunctions

| Test | Purpose |
|------|---------|
| `test_save_and_load_api_key` | Roundtrip API key to .env file |
| `test_load_api_key_from_env_var` | Falls back to environment variable |
| `test_save_and_load_seat_mapping` | Roundtrip seat mapping to TOML |
| `test_save_and_load_corrections` | Roundtrip corrections to TOML |

### TestMainWindow

| Test | Purpose |
|------|---------|
| `test_main_window_initial_state` | Convert/Cancel buttons disabled on start |
| `test_convert_button_disabled_without_inputs` | Button disabled without all inputs |
| `test_convert_button_enabled_with_valid_inputs` | Button enabled with all valid inputs |

## Test Fixtures

Located in `tests/fixtures/`:
- `sample_hands.txt` - Two hands from PLO-5Gold5 table for integration testing
- `sample_screenshot.png` - Screenshot matching hand #OM262735460
- `expected_results.toml` - Expected OCR results for the fixture screenshot
