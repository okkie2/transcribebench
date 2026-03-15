# TranscribeBench

A reproducible local benchmark tool for comparing Dutch transcription setups on Apple Silicon.

## 🎯 Goal
Build a **reproducible local benchmark** that compares serious, practical large-model transcription setups — starting with a **Metal/MLX Whisper baseline** and a handful of challenger engines — on a fixed Dutch Common Voice subset.

## ✅ Scope (v1)
- **Language:** Dutch (`nl`) only
- **Dataset:** reproducible subset from Mozilla Common Voice (cached locally)
- **Engines:**
  - `mlx-whisper` / Metal (baseline)
  - `faster-whisper`
  - `whisper.cpp`
- **Benchmark outputs:**
  - WER, CER, runtime, real-time factor, failures
  - Markdown, JSON, CSV reports
- **Design:**
  - modular pipeline (dataset provider, engine adapters, runner, report generator)
  - configuration via file (no hard-coded values)
  - CLI with `setup`, `fetch-dataset`, `run-benchmark`, `report`

## 🧩 Project layout
- `src/transcribebench/` — source code
- `config.yaml` — example configuration (YAML preferred)
- `TODO.md` — roadmap + next steps
- `tests/` — unit tests for core logic

## 🧠 Benchmark philosophy
This project is intentionally narrow and pragmatic. The goal is to compare **practical large-model transcription setups** on a realistic Dutch dataset, focusing on:
- reproducibility (fixed dataset subset + fixed seed)
- clear, comparable outputs (WER/CER + runtime metrics)
- minimal “magic” (no hidden autotuning or random sampling)

## 🧰 Supported engines (v1)
- **MLX Whisper** (Metal / Apple Silicon) — baseline (requires an MLX-converted model)
- **faster-whisper** — PyTorch/MPS challenger
- **whisper.cpp** — C++ inference (stubbed in v1)

## 🗂 Dataset source
This benchmark is designed to use a deterministic subset of **Mozilla Common Voice** (Dutch), downloaded and cached locally.

The dataset archive URL is configurable via `dataset.url`.

- If the archive is reachable, it will be downloaded and extracted.
- If the download fails (e.g., because the upstream URL changed or network access is restricted), the tool will fall back to a small **synthetic dataset** (tone audio + dummy transcripts) so the benchmark pipeline can still run.

You can also point `dataset.url` at a local archive (e.g., `file:///path/to/nl.tar.gz`) to avoid network downloads.

## 🚀 Quick start (v1)
```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .

# Optional: install engine dependencies for a true benchmark
pip install "faster-whisper" torch mlx-whisper

# Optional (MLX Whisper): prepare a converted model
# See README/ARCHITECTURE for notes on MLX model preparation.

# Inspect / edit config.yaml
python -m transcribebench.cli fetch-dataset
python -m transcribebench.cli run-benchmark
python -m transcribebench.cli report
```

## 🧩 Submodule setup
This project uses `whisper.cpp` as a git submodule (under `third_party/whisper.cpp`) to keep the outer repo clean.

If you clone the repo fresh, initialize and update the submodule before running the benchmark:

```bash
git submodule update --init --recursive
```

## 📌 Notes
- This repo is intentionally **not** trying to be an exhaustive benchmark suite.
- The focus is on **practical reproducibility**, so we keep the first release narrow and clear.
