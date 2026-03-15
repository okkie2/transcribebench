# Makefile for TranscribeBench
# Usage:
#   make setup      - initialize submodule + build whisper.cpp
#   make fetch      - refresh dataset cache (uses config/default.yaml)
#   make run        - run benchmark (uses config/default.yaml)
#   make bench      - shortcut alias for run
#   make menu       - open interactive CLI menu
#   make report     - generate report (uses config/default.yaml)
#   make clean      - remove generated artifacts/cache

.PHONY: setup submodule build-whispercpp build-apple-speech-helper fetch run bench menu report clean

PYTHON := $(shell [ -x .venv/bin/python ] && echo .venv/bin/python || echo python)
CONFIG := config/default.yaml

setup: submodule build-whispercpp

submodule:
	git submodule update --init --recursive

build-whispercpp:
	cd third_party/whisper.cpp && make

build-apple-speech-helper:
	mkdir -p .cache/apple_speech .cache/swift-module-cache
	SWIFT_MODULECACHE_PATH=$(PWD)/.cache/swift-module-cache \
	swiftc -parse-as-library -O -o .cache/apple_speech/apple-speech-cli tools/apple_speech_cli.swift

fetch:
	$(PYTHON) -m transcribebench.cli --config $(CONFIG) refresh-dataset

run:
	$(PYTHON) -m transcribebench.cli --config $(CONFIG) run-benchmark

bench: run

menu:
	$(PYTHON) -m transcribebench.cli --config $(CONFIG)

report:
	$(PYTHON) -m transcribebench.cli --config $(CONFIG) report

clean:
	rm -rf artifacts/results/latest/* artifacts/reports/latest/*
