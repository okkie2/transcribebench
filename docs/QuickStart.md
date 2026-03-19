# Quick Start

## 1) Prepare environment

Clone the repo and initialize the whisper.cpp submodule:

```bash
git clone https://github.com/okkie2/transcribebench.git
cd transcribebench
git submodule update --init --recursive
```

Create and activate a virtual environment:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

Install optional dependencies for engine runtimes:

```bash
pip install "faster-whisper" torch mlx-whisper parakeet-mlx
```

Apple-native engines (`apple_speech`, `apple_dictation`) use a small Swift helper that is built locally from `tools/apple_speech_cli.swift`. On macOS 26+, you can build it with:

```bash
make build-apple-speech-helper
```

## 2) Start the interactive CLI UI

```bash
transcribebench
```

If you do not have the console script on your PATH yet, you can use:

```bash
python -m transcribebench.cli
```

Menu actions:
- Run benchmark (auto-handles environment preparation checks + dataset cache refresh when needed)
- Set sample size
- Select engine/model pairs
- Show status

Notes for Apple-native engines:
- `apple_speech` uses `SpeechTranscriber`
- `apple_dictation` uses `DictationTranscriber`
- On this machine, Dutch (`nl-NL`) works via `apple_dictation`

## 3) Run benchmark

Choose `Run benchmark` from the menu.

## 4) View output

Benchmark run outputs:
- `artifacts/results/latest/results.json`
- `artifacts/reports/latest/report.md`
- `artifacts/reports/latest/results.csv`

`latest` is intended for the current working run. For a benchmark you want to keep in git, use a dated archive location such as:
- `artifacts/results/archive/runs_200_nl_2026-03-19/results.json`
- `artifacts/reports/archive/reports_200_nl_2026-03-19/report.md`
- `artifacts/reports/archive/reports_200_nl_2026-03-19/results.csv`

`report.md` contains:
- a compact benchmark metadata table
- a per engine/model overview table with WER, CER, and time

Preferred CLI subcommands (if needed):
- `transcribebench prepare-environment`
- `transcribebench refresh-dataset`

Legacy aliases still supported:
- `make setup`
- `make fetch`
- `make bench`
- `make report`
