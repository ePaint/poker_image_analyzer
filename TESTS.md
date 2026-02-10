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
| `test_default_settings_is_empty_dict` | Verifies DEFAULT_SETTINGS is empty |

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
