# TenneT Balance Delta High Resolution

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)
[![GitHub Release](https://img.shields.io/github/release/aritmeester/tennet_balance.svg)](https://github.com/aritmeester/tennet_balance/releases)
[![GitHub Issues](https://img.shields.io/github/issues/aritmeester/tennet_balance)](https://github.com/aritmeester/tennet_balance/issues)


[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=aritmeester&repository=tennet_balance&category=integration)

Home Assistant custom integration for the TenneT Balance Delta High Resolution API.

This integration retrieves near real-time balancing market data and exposes all numeric values as Home Assistant sensors.

## Attribution

Data provided by **TenneT** (https://www.tennet.eu).  
This project is not affiliated with or endorsed by TenneT.

## Features

- Fully asynchronous
- One sensor per data point
- HACS compatible
- Config Flow based setup

## Installation

### HACS (recommended)

1. Add this repository as a custom repository in HACS
2. Select **Integration**
3. Install **TenneT Balance Delta High Resolution**
4. Restart Home Assistant
5. Add the integration via **Settings → Devices & Services**

### Manual

Copy `custom_components/tennet_balance` into your Home Assistant config directory.

## Configuration

You need:
- A TenneT API key

An API key can be created via https://developer.tennet.eu/api-keys. Make sure the API key is created for the selected environment. To create an API key, a developer account is required, which can be requested via https://developer.tennet.eu/register/. Approval of a developer account may take several days.

Configuration is done via the UI.

## Sensors

Each numeric field in the API response is exposed as a sensor.

All sensors include:
- start time
- end time

as extra attributes.

## Update strategy

The integration schedules the next update every 12 seconds ensuring minimal delay and compliance with API guidelines.

## Debugging

Enable debug logging:

```yaml
logger:
  default: info
  logs:
    custom_components.tennet_balance: debug
