# TrueNAS API

[![GitHub Release][releases-shield]][releases]
[![GitHub Activity][commits-shield]][commits]
[![License][license-shield]](LICENSE)

![Project Maintenance][maintenance-shield]
[![Community Forum][forum-shield]][forum]

_Integration to retrieve information from TrueNAS 25.10+ ver Websocket via JSON-RPC 2.0._

TrueNAS integrations tended to use the now deprecated methods of retrieving data from TrueNAS and/or
had issues with stability/availability on my personal installation of HA.
This, combined with the reduction in exposed data via SNMP, has led me to write my own integration
for Home Assistant as a learning exercise.

The goals of this project are simple:
- create a device that represents a TrueNAS connection, with its offline and online status defined by the web socket connection state ONLY
- create entities for each major section of the TrueNAS API that are readable
- ensure it uses API tokens only to ensure no user/password information is saved in HA or exchanged.

At the moment, it provides the bare minimum of what I consider acceptable, and has been running constantly for extended periods with no
observed memory leaks or other issues.

## Installation

1. Using the tool of choice open the directory (folder) for your HA configuration (where you find `configuration.yaml`).
1. If you do not have a `custom_components` directory (folder) there, you need to create it.
1. In the `custom_components` directory (folder) create a new folder called `ha_truenas_api`.
1. Download _all_ the files from the `custom_components/ha_truenas_api/` directory (folder) in this repository.
1. Place the files you downloaded in the new directory (folder) you created.
1. Restart Home Assistant
1. In the HA UI go to "Configuration" -> "Integrations" click "+" and search for "TrueNAS API"

## Configuration is done in the UI

<!---->

## Contributions are welcome!

If you want to contribute to this please read the [Contribution guidelines](CONTRIBUTING.md)

***
[commits-shield]: https://img.shields.io/github/commit-activity/y/sammiq/ha-truenas-api.svg?style=for-the-badge
[commits]: https://github.com/sammiq/ha-truenas-api/commits/main
[forum-shield]: https://img.shields.io/badge/community-forum-brightgreen.svg?style=for-the-badge
[forum]: https://community.home-assistant.io/
[license-shield]: https://img.shields.io/github/license/sammiq/ha-truenas-api.svg?style=for-the-badge
[maintenance-shield]: https://img.shields.io/badge/maintainer-%40sammiq-blue.svg?style=for-the-badge
[releases-shield]: https://img.shields.io/github/release/sammiq/ha-truenas-api.svg?style=for-the-badge

[releases]: https://github.com/sammiq/ha-truenas-api/releases
