# Astral Pool Viron eQuilibrium Chlorinator - MQTT edition (fork)

> **This is a fork of [pbutterworth/astralpool_chlorinator](https://github.com/pbutterworth/astralpool_chlorinator)**,
> modified to consume chlorinator state from MQTT instead of talking
> Bluetooth directly from the Home Assistant host.
>
> **Why**: the original integration needs the chlorinator within BLE range
> of Home Assistant (or an ESPHome Bluetooth proxy). If your pool equipment
> is out of range like ours, a companion project runs the actual BLE
> connection on a Raspberry Pi near the equipment instead, and publishes
> the decrypted state to MQTT:
> [trastle/astral-pool-api-reverse-engineering](https://github.com/trastle/astral-pool-api-reverse-engineering).
>
> **What changed**: `coordinator.py` subscribes to `chlorinator/<name>/state`
> via Home Assistant's own MQTT connection instead of polling over
> Bluetooth; a new `mqtt_client.py` publishes writes to
> `chlorinator/<name>/action` and `chlorinator/<name>/setup` instead of
> writing directly over BLE; `config_flow.py` just asks for the device name
> segment instead of a BLE address + access code. **Every entity platform
> file (`sensor.py`, `binary_sensor.py`, `select.py`, `number.py`,
> `button.py`) is completely unmodified** - they only ever talk to
> `coordinator.data` and `coordinator.chlorinator`, which still behave the
> same shape as the original.
>
> **Write support status**: the write path (mode/speed select, setpoint
> numbers, action buttons) publishes MQTT messages correctly, but as of
> this fork's initial version the companion Pi bridge doesn't yet subscribe
> to or act on `action`/`setup` - so using those controls is currently a
> safe no-op, not yet reaching the real device. That's deliberate, pending
> the Pi bridge's write support being built.

---

# Astral Pool Viron eQuilibrium Chlorinator

[![GitHub Release][releases-shield]][releases]
[![GitHub Activity][commits-shield]][commits]
[![License][license-shield]](LICENSE)

[![pre-commit][pre-commit-shield]][pre-commit]
[![Black][black-shield]][black]

[![hacs][hacsbadge]][hacs]
[![Project Maintenance][maintenance-shield]][user_profile]

[![Community Forum][forum-shield]][forum]

[![BuyMeCoffee][buymecoffeebadge]][buymecoffee]

\**This component will set up the following platforms.**

| Platform        | Description                                                               |
| --------------- | ------------------------------------------------------------------------- |
| `binary_sensor` | Show something `True` or `False`.                                         |
| `sensor`        | Show info from Astral Pool Viron eQuilibrium Chlorinator API.             |
| `select`        | Control the chlorinator mode (off/auto/manual), pump speed, and default manual speed. |
| `number`        | Set pH setpoint, chlorine output level (0-8 manual / ORP mV automatic), and acid dosing inhibit period. |
| `button`        | Dismiss info message, disable/re-enable acid dosing, reset statistics, trigger cell reversal. |


## Installation

1. Using the tool of choice open the directory (folder) for your HA configuration (where you find `configuration.yaml`).
2. If you do not have a `custom_components` directory (folder) there, you need to create it.
3. In the `custom_components` directory (folder) create a new folder called `astralpool_chlorinator`.
4. Download _all_ the files from the `custom_components/astralpool_chlorinator/` directory (folder) in this repository.
5. Place the files you downloaded in the new directory (folder) you created.
6. Restart Home Assistant
7. Go to **Settings → Devices & Services → Add Integration**, search for
   "Astral Pool", and enter the device name segment your MQTT bridge
   publishes to (e.g. if it publishes `chlorinator/pool01/state`, enter
   `pool01`). No Bluetooth discovery in this fork - the Pi bridge already
   found the device.

Using your HA configuration directory (folder) as a starting point you should now also have this:

```text
custom_components/astralpool_chlorinator/translations/en.json
custom_components/astralpool_chlorinator/translations/fr.json
custom_components/astralpool_chlorinator/translations/nb.json
custom_components/astralpool_chlorinator/translations/sensor.en.json
custom_components/astralpool_chlorinator/translations/sensor.fr.json
custom_components/astralpool_chlorinator/translations/sensor.nb.json
custom_components/astralpool_chlorinator/translations/sensor.nb.json
custom_components/astralpool_chlorinator/__init__.py
custom_components/astralpool_chlorinator/api.py
custom_components/astralpool_chlorinator/binary_sensor.py
custom_components/astralpool_chlorinator/config_flow.py
custom_components/astralpool_chlorinator/const.py
custom_components/astralpool_chlorinator/manifest.json
custom_components/astralpool_chlorinator/sensor.py
custom_components/astralpool_chlorinator/switch.py
```

## Configuration is done in the UI

Configuration is just the device name segment, entered once during setup -
there's no poll interval to configure here since this integration doesn't
poll: it's push-based, updating whenever the Pi bridge publishes a new MQTT
message (that bridge has its own poll interval, configured on the Pi
itself).

## Credits

This project was generated from [@oncleben31](https://github.com/oncleben31)'s [Home Assistant Custom Component Cookiecutter](https://github.com/oncleben31/cookiecutter-homeassistant-custom-component) template.

Code template was mainly taken from [@Ludeeus](https://github.com/ludeeus)'s [integration_blueprint][integration_blueprint] template

---

[integration_blueprint]: https://github.com/custom-components/integration_blueprint
[black]: https://github.com/psf/black
[black-shield]: https://img.shields.io/badge/code%20style-black-000000.svg?style=for-the-badge
[commits-shield]: https://img.shields.io/github/commit-activity/y/pbutterworth/astralpool_chlorinator.svg?style=for-the-badge
[commits]: https://github.com/pbutterworth/astralpool_chlorinator/commits/main
[hacs]: https://hacs.xyz
[hacsbadge]: https://img.shields.io/badge/HACS-Custom-orange.svg?style=for-the-badge
[forum-shield]: https://img.shields.io/badge/community-forum-brightgreen.svg?style=for-the-badge
[forum]: https://community.home-assistant.io/
[license-shield]: https://img.shields.io/github/license/pbutterworth/astralpool_chlorinator.svg?style=for-the-badge
[maintenance-shield]: https://img.shields.io/badge/maintainer-%40pbutterworth-blue.svg?style=for-the-badge
[pre-commit]: https://github.com/pre-commit/pre-commit
[pre-commit-shield]: https://img.shields.io/badge/pre--commit-enabled-brightgreen?style=for-the-badge
[releases-shield]: https://img.shields.io/github/release/pbutterworth/astralpool_chlorinator.svg?style=for-the-badge
[releases]: https://github.com/pbutterworth/astralpool_chlorinator/releases
[user_profile]: https://github.com/pbutterworth
[buymecoffee]: https://www.buymeacoffee.com/pbutterworQ
[buymecoffeebadge]: https://img.shields.io/badge/buy%20me%20a%20coffee-donate-yellow.svg?style=for-the-badge
