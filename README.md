# Daikin Control Cloud - Home Assistant Integration

[![HACS Custom](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)
[![GitHub Release](https://img.shields.io/github/release/cothal/ha-daikin-control.svg)](https://github.com/cothal/ha-daikin-control/releases)

Home Assistant integration for **Daikin/Rotex** heating systems that use the [daikin-control.com](https://www.daikin-control.com) cloud service (formerly rotex-control.com).

This integration is designed for systems using the **RoCon G1 Gateway** to upload data to the Daikin Control Cloud.

## Supported Systems

- Rotex HPSU (Heat Pump) series
- Daikin Altherma (with RoCon controller)
- Any Daikin/Rotex heating system connected via RoCon G1 Gateway to daikin-control.com

## Features

- Automatic login and session management (sessions auto-renew every 6 hours)
- Sensors for all available parameters:
  - Temperatures: outdoor, supply, return, boiler, room, storage tank
  - Flow rate (Volumenstrom)
  - Pump and compressor runtime
  - Heating program status
  - Error codes
- Two device entities: heating circuit (HC1) and hot water circuit (HG1)
- Configurable polling interval (default: 120 seconds)

## Prerequisites

- A Daikin/Rotex heating system with RoCon G1 Gateway
- An active account on [daikin-control.com](https://www.daikin-control.com)
- Your **Installation ID** (visible in the daikin-control.com URL or overview page)

## Installation

### HACS (Recommended)

1. Open HACS in Home Assistant
2. Click the three dots in the top right corner
3. Select **Custom repositories**
4. Add `https://github.com/cothal/ha-daikin-control` with category **Integration**
5. Click **Download**
6. Restart Home Assistant

### Manual Installation

1. Copy the `custom_components/daikin_control` folder to your Home Assistant `config/custom_components/` directory
2. Restart Home Assistant

## Configuration

1. Go to **Settings** > **Devices & Services** > **Add Integration**
2. Search for **Daikin Control Cloud**
3. Enter your credentials:
   - **Username**: Your daikin-control.com username
   - **Password**: Your daikin-control.com password
   - **Installation ID**: Your installation ID (e.g., `AB1234CD56EF` - visible on the overview page at daikin-control.com)
   - **Scan interval**: Polling interval in seconds (default: 120, minimum: 30)

## Available Sensors

| Sensor | Unit | Description |
|--------|------|-------------|
| Aussentemperatur | °C | Outdoor temperature |
| Vorlauf Isttemperatur | °C | Supply temperature (actual) |
| Vorlauf Solltemperatur | °C | Supply temperature (target) |
| Ruecklauftemperatur | °C | Return temperature |
| Kessel Isttemperatur | °C | Boiler temperature (actual) |
| Kessel Solltemperatur | °C | Boiler temperature (target) |
| Speicher Isttemperatur | °C | Storage tank temperature |
| Raum Isttemperatur | °C | Room temperature (actual) |
| Volumenstrom | l/h | Flow rate |
| Pumpenlaufzeit | h | Pump runtime |
| Kompressorlaufzeit | h | Compressor runtime |
| Heizkurve | - | Heating curve |
| Programmschalter | - | Program switch status |
| Warmwasser aktiv | - | Hot water active |
| Aktueller Fehler | - | Current error code |

## Notes

- The integration polls the Daikin cloud API. Setting the scan interval too low (< 60s) may cause rate limiting.
- Session cookies are valid for 6 hours and are automatically renewed.
- This integration is **read-only** - it cannot change settings on your heating system.

## Background

The RoCon G1 Gateway uploads data from your Daikin/Rotex heating system to the Daikin Control Cloud. This integration reads that data and makes it available in Home Assistant. It was reverse-engineered from the daikin-control.com web interface.

Rotex Heating Systems was acquired by Daikin in 2020. The cloud service was rebranded from rotex-control.com to daikin-control.com.

## License

MIT License - see [LICENSE](LICENSE) for details.
