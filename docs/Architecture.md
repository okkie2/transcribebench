# Architecture Overview

The core vocabulary used in this architecture is defined in **docs/ubiquitous-language.md**.

This project is built around a simple, modular pipeline:

1. **Dataset provider** — fetches and caches a deterministic Common Voice subset.
2. **Engine adapters** — each `EngineAdapter` implements a `transcribe()` method and provides consistent output.
3. **Runner** — iterates over samples and enabled engine/model pairs, storing benchmark run results (JSON) and benchmark reports.
4. **Report generator** — converts benchmark run results into Markdown/CSV benchmark reports.

## Engines (plugins)
Each engine has its own adapter under `src/transcribebench/engines/`. Models are configured separately in `config/default.yaml` (an adapter can run multiple models). New engines can be added by implementing:

- `check_requirements()`
- `transcribe(audio_path, model, language, **kwargs)`

Engine/model pair selection is configured via files in `config/` (for example `config/default.yaml`):

```yaml
engines:
  - engine: mlx_whisper
    model: whisper-large-v3
    enabled: true
  - engine: parakeet_mlx
    model: parakeet-ctc-1.1b
    enabled: false
```
