# TenneT Balance Delta High Resolution

[![hacs_badge](https://img.shields.io/badge/HACS-Integration-41BDF5.svg)](https://github.com/hacs/integration)
[![GitHub Release](https://img.shields.io/github/release/aritmeester/tennet_balance.svg)](https://github.com/aritmeester/tennet_balance/releases)
[![GitHub Issues](https://img.shields.io/github/issues/aritmeester/tennet_balance)](https://github.com/aritmeester/tennet_balance/issues)

Home Assistant custom integration for the TenneT Balance Delta High Resolution API.

This integration retrieves near real-time balancing market data and exposes all numeric values as Home Assistant sensors.

## Attribution

Data provided by **TenneT** (https://www.tennet.eu).  
This project is not affiliated with or endorsed by TenneT.

## Features

- Fully asynchronous
- One sensor per numeric data point plus a binary sensor for emergency power detection
- Additional rule-state sensors for previous quarter-hour (final) and current quarter-hour prediction:
  - enum states: `down`, `neutral`, `up`, `both`
  - labels include numeric state mapping for recognition (`-1`, `0`, `1`, `2`)
  - experimental: determination logic is currently under evaluation and may change
- `power_mari_in` and `power_mari_out` are disabled by default (available to enable manually)
- Optional diagnostic sensors are available (disabled by default): last successful API update, API response time, and consecutive API failures
- HACS compatible
- Config Flow based setup

## Installation

[![Open your Home Assistant instance and install this integration via HACS.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=aritmeester&repository=tennet_balance&category=integration)
[![Open your Home Assistant instance and start setting up this integration.](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=tennet_balance)

### HACS (recommended)

1. Install **TenneT Balance Delta High Resolution** via HACS (button above).
2. Restart Home Assistant.
3. Add the integration via **Settings → Devices & Services** (or use the setup button above).

## Configuration

You need:
- A TenneT API key

An API key can be created via [developer.tennet.eu/api-keys](https://developer.tennet.eu/api-keys). Make sure the API key is created for the selected environment.

To create an API key, a developer account is required. You can request one via [developer.tennet.eu/register](https://developer.tennet.eu/register/). Approval may take several days.

Configuration is done via the UI.

Available options:

- `keep_last_regulation_prices`: keep the last known regulation price when the API returns `null`.
- Update API key via **Settings → Devices & Services → TenneT Balance Delta → Configure**.

### Multiple environments

The integration supports both Production (`api`) and Acceptance (`api.acc`) environments.
Only one config entry per environment is allowed.

## Sensors

Each numeric field in the API response is exposed as a sensor.

All sensors include:
- start time
- end time

as extra attributes.

The regulation state sensors apply dummy-energy filtering for aFRR:
- upward direction (`in`) only counts when upward price is present
- downward direction (`out`) only counts when downward price is present

The current quarter-hour sensor is a prediction based on snapshots received so far.

## Update strategy

The integration schedules the next update every 12 seconds ensuring minimal delay and compliance with API guidelines.

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for release history.

## Debugging

Enable debug logging:

```yaml
logger:
  default: info
  logs:
    custom_components.tennet_balance: debug

## Troubleshooting

- If the API returns `{"error":"No data found"}`, the integration treats this as an API error for that update.
- If the API returns a structured error payload (for example with `Error_message`), the update is also marked as failed.
- During failed updates, point-based sensors become unavailable until valid data is received again.
- Diagnostic sensor `API - Consecutive Failures` exposes:
  - `last_error`
  - `last_error_details` (including error type/message and payload details when available)
- Full integration diagnostics are available via **Settings → Devices & Services → TenneT Balance Delta → Download diagnostics**.
