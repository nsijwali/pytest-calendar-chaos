# Contributing

## Setup

```
uv sync
```

## Checks (run before opening a PR)

```
uv run pytest
uv run ruff check . && uv run ruff format --check .
uv run mypy src
```

Optional: `uv run pre-commit install` to run ruff and file hygiene hooks on commit.

## Proposing a calendar case

Good cases are the product. Open a "New calendar case" issue, or a PR, with:

- the exact date or time (and zone, if it matters),
- why it breaks code,
- a short real-world bug example that fails at that moment.

## Case IDs are a public API

Saved reproduce commands depend on case IDs.

- Adding cases is a minor release.
- Renaming or removing a case ID is a breaking change.

## Rules

- All clock mocking goes through `time-machine`; never patch `datetime` directly.
- `catalog.py` and `dst.py` must not import pytest.
- Add dependencies only with a clear justification.
