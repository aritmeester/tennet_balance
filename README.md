# TenneT Balance Delta High Resolution

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)
[![GitHub Release](https://img.shields.io/github/release/aritmeester/tennet_balance.svg)](https://github.com/aritmeester/tennet_balance/releases)
[![GitHub Issues](https://img.shields.io/github/issues/aritmeester/tennet_balance)](https://github.com/aritmeester/tennet_balance/issues)


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
