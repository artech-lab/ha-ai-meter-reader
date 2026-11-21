# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses
[Semantic Versioning](https://semver.org/).

## [Unreleased]

## [1.1.0] - 2026-11-21

### Added

- The wheels of the card counter can be turned to correct the reading: tap the counter, turn the wheels with
  the arrows, the mouse wheel, a vertical drag or the keyboard, then confirm. The card calls
  `ai_meter_reader.set_reading`; a value lower than the current reading is pointed out before confirming.
- The counter wheels roll to the new digits when the reading changes.

### Changed

- The consumption tiles of today, yesterday and the last 24 hours have an icon, a translucent background and
  larger figures in the color of the meter type.
- Tapping the counter no longer opens the history of the reading (the header and the chart still do).

## [1.0.1] - 2026-11-17

### Fixed

- A digit misread the same way on every frame (for example the first wheel hidden by the flash reflection
  and read as 9) could be confirmed and accepted. A jump larger than a whole day at the maximum increase
  (or than the time since the last accepted value at that rate, if longer) is now rejected as `implausible`
  however many readings agree, and counts towards the problem alert.
- An AI Task call that timed out was reported with an empty error (`ai_task.x: `): the last error now names the
  exception (`TimeoutError`).

## [1.0.0] - 2026-11-16

### Added

- Readings of water, gas and electricity or heat meters from any camera entity through any AI Task entity
  that reads images: one frame at a time, with optional camera light and warm-up, a retry of unreadable
  frames and a fallback AI Task entity.
- The AI copies digits only; decimal digits, digit count and confidence are checked by the integration.
- Plausibility check: decreases are rejected, larger-than-allowed increases wait for confirmation by the
  next readings, the allowed increase scales with the time since the last accepted value.
- `total_increasing` reading sensor with the device class of the meter, ready for the Energy dashboard.
- Last frame image entity, last result, confidence, read now button, automatic reading switch, maximum
  increase per reading number, problem alert after three failed readings in a row, `set_reading` action.
- Bundled dashboard card, served and loaded by the integration: counter, today / yesterday / last 24 h,
  hourly chart, last frame, result and confidence.
- English and Italian translations.
