# Makefile for TranscribeBench
# Usage:
#   make setup      - initialize submodule + build whisper.cpp
#   make fetch      - fetch dataset (uses config.yaml)
#   make run        - run benchmark (uses config.yaml)
#   make report     - generate report (uses config.yaml)
#   make clean      - remove generated runs/reports

.PHONY: setup submodule build-whispercpp fetch run report clean

setup: submodule build-whispercpp

submodule:
	git submodule update --init --recursive

build-whispercpp:
	cd third_party/whisper.cpp && make

fetch:
	python -m transcribebench.cli fetch-dataset

run:
	python -m transcribebench.cli run-benchmark

report:
	python -m transcribebench.cli report

clean:
	rm -rf runs reports runs_* reports_*
