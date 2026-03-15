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

## 2) Fetch dataset

```bash
make fetch
```

## 3) Run benchmark

```bash
make run
```

## 4) Generate report

```bash
make report
```
