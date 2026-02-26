# Changelog

## Unreleased

## 2602.26.1b2

Changes since 2602.26.1b1:

### Changed

- Removed `TenneT` from device `DeviceInfo.name` to avoid duplicate vendor naming.
- Updated sensor and binary sensor naming so friendly names no longer include the device name prefix.
- Updated Dutch regulation prediction label to: `Huidig kwartier (prognose)`.

## 2602.26.1b1

Changes since 2602.25.1b1:

### Added

- Added two enum sensors for regulation state:
	- previous quarter-hour (final)
	- current quarter-hour prediction
- Enum sensor values are now `down`, `neutral`, `up`, `both`.
- Enum labels include the numeric mapping for recognition (`-1`, `0`, `1`, `2`).
- Added dummy-energy aware filtering for aFRR activations in Regulation State 2 logic:
	- `power_afrr_in` only counts when `max_upw_regulation_price` is present
	- `power_afrr_out` only counts when `min_downw_regulation_price` is present
- Added dynamic icons for enum regulation state values.
- Marked regulation state determination as experimental/in evaluation; logic and outcomes may change.
- Added optional diagnostic sensors (disabled by default): API last successful update, API response time, and API consecutive failures.

### Changed

- Removed the dedicated Regulation State 2 binary sensors and numeric regulation state sensors.
- Set `power_mari_in` and `power_mari_out` sensors to disabled by default (they remain available for manual enable).
- Price units now report as `€/MWh` instead of `€`.

### Fixed

- API error payloads are now handled explicitly, including both `{"error":"No data found"}` and structured `Error_message` responses.
- Failed API updates (including no-data responses) now make point-based sensors unavailable instead of silently exposing empty values.
- Added structured API error context to diagnostics (`api_last_error_details`) for easier troubleshooting.

## 2623.23.1

Changes since 2602.23.0:

### Fixed

- Fixed emergency power binary sensor state translations by moving state labels to the correct translation key path (`entity.binary_sensor.emergency_power_activated.state`).
- Improved readability of emergency power status wording in English and Dutch.

## 2602.23.0

Changes since 2602.18.0:

### Added

- Added setting `keep_last_regulation_prices` in the initial setup flow and options flow.
- Added full runtime translations (`en` and `nl`) for config flow, options flow and entity names.
- Added translated entity naming via `translation_key` for all sensors and the binary sensor.
- Added reauthentication flow for invalid API keys.
- Added ability to update the API key from the options flow.

### Changed

- Config entry titles now include the selected environment (e.g. Production/Acceptance), with Dutch labels when HA language is Dutch.
- Setup now prevents duplicate entries for the same environment.
- Entity IDs now support environment-scoped unique IDs for multi-environment setups, with backward compatibility for existing entities.
- Price sensor labels were updated for better alphabetical grouping (`Price - ...` / `Prijs - ...`).
- API client now uses Home Assistant's shared aiohttp session.

### Fixed

- Fixed options flow crash (`config_entry` read-only property issue) by migrating to `OptionsFlowWithConfigEntry`.
- Fixed binary sensor logic to read from `latest_point` instead of the raw API envelope.
- Added binary sensor availability handling based on point availability.
- Fixed invalid state class usage for monetary sensors.
- Improved API resilience with retry/backoff for transient network/API errors.
- Fixed auth failure handling: `401/403` now trigger `ConfigEntryAuthFailed` and reauth instead of repeated setup retries.