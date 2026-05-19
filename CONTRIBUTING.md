# Contributing to ETS

## Local Setup

Use Python 3.12 or newer.

```powershell
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
```

## Checks

```powershell
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m ruff check .
```

Core protocol code must stay independent of API, persistence, and UI runtime
dependencies.
