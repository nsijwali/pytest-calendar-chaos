# Changelog

All notable changes to this project are documented here.
Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versioning: [SemVer](https://semver.org/).

## [0.5.0] - 2026-11-01

### Added
- `century` preset: leap day 2000, and Feb 28 / Mar 1 2100 (not a leap year), plus the last
  microsecond of Feb 28 2100.
- `iso_week` cases for leap year 2020, which also has 53 ISO weeks
  (`iso-week-53-leap-2020-12-31`, `iso-week-53-new-year-2021`).
- `dst` cases at the exact transition instant: `dst-spring-at-2027` and `dst-fall-at-2027`.
  Suites using `cases=["dst"]` now run two more scenarios per zone with DST.

### Changed
- **Marker arguments are validated.** Unknown keyword arguments (for example `zone=` instead of
  `zones=`), extra positional arguments, non-string entries in `cases`/`zones` and a non-boolean
  `tick` are now collection errors. Previously `zone=[...]` was silently ignored and the test ran
  in UTC. A marker that relied on that will now fail with a clear message.
- Reproduce commands are quoted for the user's shell (`shlex` on POSIX, Windows rules on Windows).
  Test IDs containing `$(...)`, backticks or spaces now paste safely; the path in the second
  command is quoted too. Quotes in the printed command change from `"..."` to `'...'` on POSIX.
- DST transitions are cached per zone and year, so repeated expansion no longer rescans the year.
- README: odd UTC offsets, the tz database policy, and the new cases.

## [0.4.1] - 2026-10-23

### Changed
- README: document that `tick=False` freezes `time.time()` and `datetime.now()` (so wall-clock wait
  loops hang), and that `time.monotonic()`, `time.perf_counter()` and the asyncio loop clock are
  not mocked.
- Release workflow: the TestPyPI verify step now installs only this package from TestPyPI
  (`--no-deps`) and takes its dependencies from PyPI.
- Development lock file: resolve only packages that are at least a week old (`exclude-newer`).
- Internal: removed an unused value in the marker parsing.

## [0.4.0] - 2026-10-23

### Added
- `iso_week` preset: ISO week 53 of 2026 and the first ISO week of 2027
  (`iso-week-53-2026-12-31`, `iso-week-53-new-year-2027`, `iso-week-1-2027-01-04`).
- `y2038` preset: the signed 32-bit `time_t` limit (`y2038-before-limit`,
  `y2038-last-valid-second`, `y2038-after-limit`). These are absolute UTC instants and are the
  same moment in every zone.
- `Case.utc` field (default `False`). For `utc=True` cases, `wall_time` is a UTC time instead of a
  local wall-clock time.

## [0.3.1] - 2026-10-23

### Changed
- README: plain-language intro and a demo recording, so the PyPI page matches the GitHub page.
- Release workflow: the TestPyPI verify step now retries for about five minutes instead of two,
  because TestPyPI's index can lag behind an upload.

## [0.3.0] - 2026-10-23

### Added
- `--calendar-chaos-list` prints the case catalog and exits without running tests.
- `calendar_chaos_default_zones` ini option sets the default zones for markers without `zones`.
- Project URLs (homepage, source, issues, changelog) in the package metadata, so the PyPI page
  links back to the repository.

### Changed
- README: badges, CLI and configuration docs, install and Windows notes.

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
