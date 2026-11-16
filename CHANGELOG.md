# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses
[Semantic Versioning](https://semver.org/).

## [Unreleased]

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
