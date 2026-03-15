# Architecture Overview

TranscribeBench is structured for modularity and clarity, with the goal of making it easy to add new dataset providers or transcription engines while keeping the benchmark pipeline consistent.

The core vocabulary used in this architecture is defined in **docs/ubiquitous-language.md**.

## Core concepts

### Dataset providers
- Implemented under `src/transcribebench/dataset/`
- Each provider must implement reproducible download + rebuildable cache behavior.
- v1 includes a **Common Voice** provider that downloads the Dutch CV archive, extracts it, and selects a deterministic subset based on seed + sample size.

### Engine adapters
- Implemented under `src/transcribebench/engines/`
- Each engine adapter implements the `EngineAdapter` interface:
  - `check_requirements()` to report missing deps
  - `transcribe(audio_path, model, language)` to return an `EngineResult`
- Current engines (stubs): `mlx_whisper`, `faster_whisper`, `whisper_cpp`

### Benchmark runner
- `src/transcribebench/runner.py` orchestrates:
  - dataset loading
  - running each engine/model pair on every sample
  - computing metrics (WER / CER, runtime)
  - saving benchmark run results + benchmark reports (JSON + CSV + Markdown)

### CLI
- `src/transcribebench/cli.py` provides a small command set:
  - `prepare-environment` — check environment requirements
  - `refresh-dataset` — refresh dataset cache
  - `run-benchmark` — run benchmark and save results
  - `report` — point to generated benchmark report artifacts

## Configuration
- YAML-based config: `config/default.yaml` (additional benchmark profiles under `config/`)
- Controls:
  - language + dataset sampling
  - enabled engines + model IDs
  - output directories
