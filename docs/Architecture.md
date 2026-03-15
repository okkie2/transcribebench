# Architecture Overview

This project is built around a simple, modular pipeline:

1. **Dataset provider** — fetches and caches a deterministic Common Voice subset.
2. **Engine adapters** — each `EngineAdapter` implements a `transcribe()` method and provides consistent output.
3. **Runner** — iterates over samples and enabled engines, storing results (JSON + reports).
4. **Report generator** — converts results into Markdown/CSV for easy comparison.

## Engines (plugins)
Each engine has its own adapter under `src/transcribebench/engines/`. New engines can be added by implementing:

- `check_requirements()`
- `transcribe(audio_path, model, language, **kwargs)`

Engine selection is configured via `config.yaml`.
