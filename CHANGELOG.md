# Changelog

## [0.1.2](https://github.com/roquerodrigo/tuya-ble-sdk/compare/v0.1.1...v0.1.2) (2026-08-23)


### Features

* read device credentials from the Tuya account ([2a5d5af](https://github.com/roquerodrigo/tuya-ble-sdk/commit/2a5d5af335eba2c374c5480f102506e5634b798d))


### Bug Fixes

* tell a rate-limited login from a rejected one ([3222c52](https://github.com/roquerodrigo/tuya-ble-sdk/commit/3222c52a6173305f7280c9b14181505a4bc26811))

## [0.1.1](https://github.com/roquerodrigo/tuya-ble-sdk/compare/v0.1.0...v0.1.1) (2026-08-19)


### Features

* implement the Tuya BLE protocol ([f309745](https://github.com/roquerodrigo/tuya-ble-sdk/commit/f309745b2a62b67af4cace38ae7ecfca2b8cf7a4))
* scaffold the Tuya BLE SDK package ([8242a3e](https://github.com/roquerodrigo/tuya-ble-sdk/commit/8242a3e7bcdccdf62f7b4385aee9d6fa2ca7d757))


### Bug Fixes

* connect at the first sighting instead of after the whole scan ([a612982](https://github.com/roquerodrigo/tuya-ble-sdk/commit/a612982a51b0b3ca0fe5c2ac7dbfa345215e3993))
* connect at the first sighting instead of after the whole scan ([b81dd11](https://github.com/roquerodrigo/tuya-ble-sdk/commit/b81dd1180359b44832d506f8071bd85621221b55))
* hash the advertised product record as broadcast ([be4c892](https://github.com/roquerodrigo/tuya-ble-sdk/commit/be4c892439a50ec4c163f61044a2d8abd811d085))
* reset the framing state between two sessions of one client ([57059c2](https://github.com/roquerodrigo/tuya-ble-sdk/commit/57059c2b1a23b0517b31704108efcff9b8ac1fe9))
* treat a report with no datapoint as an answer ([445ad3a](https://github.com/roquerodrigo/tuya-ble-sdk/commit/445ad3ac31905679a2373c89c0b461aac0883e8e))


### Documentation

* record the unparsed signed datapoint commands ([93db2a9](https://github.com/roquerodrigo/tuya-ble-sdk/commit/93db2a9cfa1530c1ea9e74d6fd6dee1e1df08c94))


### Tests

* freeze the wire bytes of the handshake commands ([18c6e86](https://github.com/roquerodrigo/tuya-ble-sdk/commit/18c6e863cbeef7d372eb4d33ea2aacd15a774484))


### Miscellaneous Chores

* let release-please own the version ([2f0a12a](https://github.com/roquerodrigo/tuya-ble-sdk/commit/2f0a12a8b9de35f55a59fc8fb119aaf5db4958c0))
