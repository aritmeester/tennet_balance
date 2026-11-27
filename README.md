# TenneT Balance Delta High Resolution

[![hacs_badge](https://img.shields.io/badge/HACS-Integration-41BDF5.svg)](https://github.com/hacs/integration)
[![GitHub Release](https://img.shields.io/github/release/aritmeester/tennet_balance.svg)](https://github.com/aritmeester/tennet_balance/releases)
[![GitHub Issues](https://img.shields.io/github/issues/aritmeester/tennet_balance)](https://github.com/aritmeester/tennet_balance/issues)
[![Validation](https://github.com/aritmeester/tennet_balance/actions/workflows/validate.yml/badge.svg)](https://github.com/aritmeester/tennet_balance/actions/workflows/validate.yml)

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

## Development & Testing

The repository includes standalone unit tests for the coordinator.
These tests use synthetic API responses and lightweight Home Assistant
stubs, allowing them to run without a Home Assistant installation
or a TenneT API key.

### Prerequisites

- Python 3.12 or newer
- Development dependencies listed in `requirements-dev.txt`

Install the development dependencies from the repository root:

```bash
python -m pip install -r requirements-dev.txt
```

The `tzdata` package provides the IANA time zone database required
by Python's `zoneinfo` module, particularly on Windows.

### Running tests

Run all unit tests from the repository root:

```bash
python -m unittest discover -s tests -v
```

To run only the coordinator cache tests:

```bash
python -m unittest discover -s tests -p test_coordinator_cache.py -v
```

### Test coverage

The coordinator cache tests cover:

- ISP analysis caching and invalidation
- Latest measurement point caching
- Empty API payload handling and recovery
- Protection against mutation of cached analysis results
- API throttling and grace period behavior
- Dynamic API data delay calculations
- Regulation price retention
- Cache isolation between coordinator instances

### Validation before releasing

Before creating a release:

1. Ensure all unit tests pass.
2. Verify the manifest version and changelog entry.
3. Ensure the Home Assistant Validate GitHub Actions workflow succeeds.
4. Follow the release procedure described in [RELEASING.md](RELEASING.md).

The standalone unit tests complement HACS and hassfest validation
but do not replace runtime testing within Home Assistant.

### Continuous Integration

The GitHub Actions workflow automatically validates the integration
on every push and pull request. It can also be triggered manually.

The workflow includes:

- HACS integration validation
- Home Assistant hassfest validation
- Python syntax validation
- Automated unit tests

Unit tests run against the following platform and Python combinations:

| Platform | Python versions |
|----------|-----------------|
| Ubuntu   | 3.12, 3.14      |
| Windows  | 3.12, 3.14      |

All validation jobs must succeed before creating a release.

See the [Home Assistant Validate workflow](.github/workflows/validate.yml)
for the complete configuration.

## Debugging

Enable debug logging:

### Via the UI (temporary, no restart)

You can enable debug logging at runtime from the Home Assistant UI:

1. Go to **Developer Tools → Services**.
2. Select the service: `logger.set_level`.
3. Use this service data:

```yaml
custom_components.tennet_balance: debug
```

To disable again:

```yaml
custom_components.tennet_balance: info
```

Note: this method resets after a Home Assistant restart.

### Via the integration menu (if available)

In some Home Assistant versions you may see **Enable debug logging** / **Disable debug logging** in the integration's three-dot menu.
If you don't see it, use the `logger.set_level` service above.

This option may be missing depending on your Home Assistant version and whether the integration exposes its logger names in its manifest.

### Via configuration.yaml (persistent)

```yaml
logger:
  default: info
  logs:
    custom_components.tennet_balance: debug
```

## Troubleshooting

- If the API returns `{"error":"No data found"}`, the integration treats this as an API error for that update.
- If the API returns a structured error payload (for example with `Error_message`), the update is also marked as failed.
- During failed updates, point-based sensors become unavailable until valid data is received again.
- Diagnostic sensor `API - Consecutive Failures` exposes:
  - `last_error`
  - `last_error_details` (including error type/message and payload details when available)
- Full integration diagnostics are available via **Settings → Devices & Services → TenneT Balance Delta → Download diagnostics**.
