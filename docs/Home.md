# TranscribeBench Wiki

This repository is a reproducible benchmark tool for Dutch speech-to-text engines on Apple Silicon.

- **Goal:** Compare real-world transcription setups using a fixed Common Voice subset.
- **Approach:** Modular engine adapters with configurable model selection, deterministic dataset sampling, and consistent metrics (WER/CER + timing).

Use the pages in this `docs/` folder as source material for the GitHub Wiki.

Start here:
- Launch the interactive CLI UI with `transcribebench` (or `python -m transcribebench.cli`)
- See [QuickStart](QuickStart) for the menu-based workflow
- See [Benchmark Methodology](Benchmark) for datasets, metrics, results, and hardware context
- See [Architecture](Architecture) for the pipeline and adapter structure
- Apple-native paths currently split into `apple_speech` (`SpeechTranscriber`) and `apple_dictation` (`DictationTranscriber`)
- Terminology reference: [Ubiquitous Language](ubiquitous-language)
