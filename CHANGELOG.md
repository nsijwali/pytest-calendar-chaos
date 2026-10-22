# Changelog

All notable changes to this project are documented here.
Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versioning: [SemVer](https://semver.org/).

## [0.2.0] - 2026-10-23

First public release.

### Added
- `calendar_chaos` marker with `cases`, `zones` and `tick`; works on functions, classes and modules.
- Presets `leap_day`, `month_end`, `year_end`, `midnight` (fixed years 2027/2028).
- `dst` preset computed per zone from `zoneinfo` for 2027, including fold-aware repeated-hour cases.
- `--calendar-case ID` option (full or base IDs, repeatable) and the `calendar_case` fixture.
- Failure section with case, zone, clock, transition and reproduce commands, plus an end-of-run
  summary of failed scenarios.
- Clock mocking through `time-machine` only.
