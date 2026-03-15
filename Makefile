# Makefile for TranscribeBench
# Usage:
#   make setup      - initialize submodule + build whisper.cpp
#   make fetch      - fetch dataset (uses config.yaml)
#   make run        - run benchmark (uses config.yaml)
#   make bench      - shortcut alias for run
#   make menu       - open interactive CLI menu
#   make report     - generate report (uses config.yaml)
#   make clean      - remove generated runs/reports

.PHONY: setup submodule build-whispercpp fetch run bench menu report clean

PYTHON := $(shell [ -x .venv/bin/python ] && echo .venv/bin/python || echo python)

setup: submodule build-whispercpp

submodule:
	git submodule update --init --recursive

build-whispercpp:
	cd third_party/whisper.cpp && make

fetch:
	$(PYTHON) -m transcribebench.cli fetch-dataset

run:
	$(PYTHON) -m transcribebench.cli run-benchmark

bench: run

menu:
	$(PYTHON) -m transcribebench.cli

report:
	$(PYTHON) -m transcribebench.cli report

clean:
	rm -rf runs reports runs_* reports_*
