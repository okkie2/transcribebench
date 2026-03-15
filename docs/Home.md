# TranscribeBench Wiki

This repository is a reproducible benchmark tool for Dutch speech-to-text engines on Apple Silicon.

- **Goal:** Compare real-world transcription setups using a fixed Common Voice subset.
- **Approach:** Modular engine adapters, deterministic dataset sampling, and consistent metrics (WER/CER + timing).

Use the pages in this `docs/` folder as source material for the GitHub Wiki.

Start here:
- Launch the interactive CLI UI with `transcribebench` (or `python -m transcribebench.cli`)
- See [QuickStart](QuickStart) for the menu-based workflow
