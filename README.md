# Daikin Control Cloud - Home Assistant Integration

[![HACS Custom](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)
[![GitHub Release](https://img.shields.io/github/release/cothal/ha-daikin-control.svg)](https://github.com/cothal/ha-daikin-control/releases)

Home Assistant integration for **Daikin/Rotex** heating systems that use the [daikin-control.com](https://www.daikin-control.com) cloud service (formerly rotex-control.com).

This integration is designed for systems using the **RoCon G1 Gateway** to upload data to the Daikin Control Cloud.

## Supported Systems

- Rotex HPSU Compact / Compact Ultra
- Daikin Altherma (with RoCon controller)
- Any Daikin/Rotex heating system connected via RoCon G1 Gateway to daikin-control.com

## Features

- **Automatic login and session management** with retry logic and resilient handling of cloud outages
- **Persistent sensor values** (RestoreSensor) - last known values survive HA restarts and brief data gaps
- **Gateway online status detection** via dedicated cloud API endpoint:
  - `binary_sensor.daikin_gateway_online` - RoCon G1 to cloud connection
  - `binary_sensor.daikin_canbus_online` - RoCon G1 to heat pump connection
  - Configurable offline threshold (60-3600 s)
- **Time-since-contact sensors** for use in automations (auto-reboot of the gateway via smart plug etc.)
- **Whitelist of important sensors** enabled by default (temperatures, flow, runtimes, status). Other parameters are created as disabled entities, can be enabled manually.
- **Configurable polling interval** (30-3600 s, default 120 s)
- **Two device entities**: heating circuit (HC1) and hot water circuit (HG1) plus a Cloud Gateway device

## Prerequisites

- A Daikin/Rotex heating system with RoCon G1 Gateway
- An active account on [daikin-control.com](https://www.daikin-control.com)
- Your **Installation ID** (visible on the overview page after login)

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
   - **Installation ID**: Your installation ID (e.g., `AB1234CD56EF`)
   - **Scan interval**: Polling interval in seconds (default 120)

After setup, you can adjust the **scan interval** and **gateway offline threshold** under the integration's *Configure* button.

## Sensors

### Heating circuit (HC1)
- Außentemperatur (outdoor)
- Vorlauf Ist-/Solltemperatur (supply actual/target)
- Rücklauftemperatur (return)
- Kessel Ist-/Solltemperatur (boiler)
- Speicher Isttemperatur (storage tank)
- Volumenstrom (l/h)
- Pumpenlaufzeit, Kompressorlaufzeit (h)
- Heizkurve, Programmschalter, Aktueller Fehler
- TVBH, TVBH-Mix, TVBH1 temperatures

### Hot water (HG1)
- Same sensors as HC1 mirrored for the hot water circuit

### Cloud / Gateway
- `binary_sensor.daikin_gateway_online` - true if RoCon G1 had cloud contact within threshold
- `binary_sensor.daikin_canbus_online` - true if RoCon G1 received CanBus data from heat pump within threshold
- `sensor.daikin_seconds_since_gateway_contact`
- `sensor.daikin_seconds_since_canbus_contact`
- `sensor.daikin_last_gateway_contact` (timestamp)
- `sensor.daikin_last_canbus_contact` (timestamp)
- `sensor.daikin_firmware_version`

## Auto-Reboot of the RoCon G1

The RoCon G1 has a tendency to lose its CanBus or cloud connection occasionally. A common solution is to put the gateway on a smart plug and reboot it automatically when the binary sensor goes offline.

Example automation:

```yaml
alias: Daikin RoCon G1 Auto-Reboot
mode: single
triggers:
  - trigger: state
    entity_id: binary_sensor.daikin_gateway_online
    to: "off"
    for:
      minutes: 5
conditions:
  - condition: template
    value_template: >
      {% set last_reboot_ts = state_attr('input_datetime.daikin_last_reboot', 'timestamp') %}
      {% if last_reboot_ts is none %}
        true
      {% else %}
        {{ (now().timestamp() - last_reboot_ts) > 1800 }}
      {% endif %}
actions:
  - action: input_datetime.set_datetime
    target:
      entity_id: input_datetime.daikin_last_reboot
    data:
      datetime: "{{ now() }}"
  - action: switch.turn_off
    target:
      entity_id: switch.shelly_rocong1
  - delay: { seconds: 30 }
  - action: switch.turn_on
    target:
      entity_id: switch.shelly_rocong1
```

## Notes

- The integration polls the Daikin cloud API. The default scan interval of 120 seconds is a sensible starting point. Below 60 seconds is not recommended.
- Session cookies are valid for 6 hours and are automatically renewed (proactively after 5 hours).
- The integration is **read-only** - it cannot change settings on the heat pump.
- Daikin's cloud only delivers parameter changes - sensors that don't change frequently may have a `last_update` timestamp that lags behind. Use the gateway online binary sensor for connectivity detection.

## Background

The RoCon G1 Gateway uploads data from your Daikin/Rotex heating system to the Daikin Control Cloud. This integration reads that data and makes it available in Home Assistant. It was reverse-engineered from the daikin-control.com web interface.

Rotex Heating Systems was acquired by Daikin in 2020. The cloud service was rebranded from rotex-control.com to daikin-control.com.

## Changelog

- **1.2.1** - Configurable offline threshold for gateway/canbus binary sensors
- **1.2.0** - Cloud gateway status binary sensors
- **1.1.0** - Persistent sensor values (RestoreSensor) - survive restarts
- **1.0.9** - Resilient error handling (retries, longer timeouts, keep last value on transient errors)
- **1.0.8** - Options flow to change scan interval without reinstall
- **1.0.7** - Proactive session refresh + better session expiry handling
- **1.0.6** - Handle 401/403 by re-logging in with fresh session
- **1.0.5** - Whitelist approach: only key sensors created
- **1.0.0** - Initial release

## License

MIT License - see [LICENSE](LICENSE) for details.
