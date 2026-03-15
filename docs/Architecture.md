# Architecture Overview

The core vocabulary used in this architecture is defined in **docs/ubiquitous-language.md**.

This project is built around a simple, modular pipeline:

1. **Dataset provider** — fetches and caches a deterministic Common Voice subset.
2. **Engine adapters** — each `EngineAdapter` implements a `transcribe()` method and provides consistent output.
3. **Runner** — iterates over samples and enabled engine/model pairs, storing benchmark run results (JSON) and benchmark reports.
4. **Report generator** — converts benchmark run results into Markdown/CSV benchmark reports.

## End-to-end benchmark flow

A benchmark run follows the same high-level sequence every time:

1. Load configuration from a YAML file in `config/`.
2. Build the list of enabled engine/model pairs.
3. Refresh or reuse the cached dataset subset.
4. Run every enabled engine/model pair against every sample in that subset.
5. Compute per-sample WER/CER and collect timing information.
6. Aggregate summary metrics and write `results.json`, `results.csv`, and `report.md`.

This keeps the runner generic while allowing engine-specific behavior to stay inside each adapter.

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

Examples of engines currently integrated:

- `apple_dictation`
- `apple_speech`
- `mlx_whisper`
- `faster_whisper`
- `whisper_cpp`
- `parakeet_mlx`

In TranscribeBench, the engine is the runtime integration layer, while the model is the set of weights loaded by that runtime.

## Dataset and results

The default dataset provider builds a reproducible Common Voice subset under `.cache/datasets/<language>/`.

The benchmark then writes outputs to:

- `artifacts/results/.../results.json`
- `artifacts/reports/.../results.csv`
- `artifacts/reports/.../report.md`

Detailed benchmark methodology, dataset structure, reproducibility rules, metric definitions, and result interpretation are documented on the [Benchmark Methodology](Benchmark) page.
