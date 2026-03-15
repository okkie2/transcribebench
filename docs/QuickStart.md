# Quick Start

## 1) Setup

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

Install optional dependencies for faster-whisper + MLX:

```bash
pip install "faster-whisper" torch mlx-whisper
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
- Run benchmark (auto-handles setup + dataset refresh when needed)
- Set sample size
- Select engines
- Show current status/configuration

## 3) Run benchmark

Choose `Run benchmark` from the menu.

## 4) View output

Generated files:
- `runs/results.json`
- `reports/report.md`
- `reports/results.csv`

Optional legacy commands:
- `make setup`
- `make fetch`
- `make bench`
- `make report`
