  # TODO / Roadmap (v1)

## Immediate next work (v1)
- [x] Implement Common Voice subset downloader and deterministic sampling
- [x] Implement basic transcription runners calling each engine adapter
- [x] Implement WER/CER calculation and validation against known ground truth
- [x] Persist raw engine transcripts and per-file timing data
- [x] Add RTF metric (`transcription_time / audio_duration`) per sample and per-engine report summary
- [x] Flesh out report generator (Markdown + JSON + CSV)
- [x] Add CI / test coverage for critical core logic
- [x] Add a dated archived benchmark snapshot for the 200-sample Dutch baseline
- [x] Document the distinction between mutable `latest` outputs and commit-worthy archived benchmark snapshots

## v1.x improvements
- Add optional GPU/Metal performance tuning knobs per engine
- Add model selection abstraction (large models only, but allow model overrides)
- Add reproducible Docker/conda environment spec
- Add support for multiple languages (after Dutch baseline is stable)
- Add optional per-engine warmup and caching (model load times)
- Add `distil-large-v3`, `nvidia/parakeet-ctc-1.1b`, `facebook/mms-1b-all` adapters
- Add benchmark configuration profiles (small/medium/large runs)
- Add a lightweight release process anchored on major/minor/patch version numbers
- Add `CHANGELOG.md` with an `Unreleased` section and versioned release entries
- Add `RELEASE_NOTES.md` templates derived from versioned changelog entries

## CLI / UX Improvements
- Improve CLI transparency when downloading speech models by printing a clear pre-download message with engine, model name, and approximate size when known (for example: `Downloading model: parakeet-ctc-1.1b (~4.2 GB)`) before the HuggingFace/tqdm progress bar starts
- [x] Add a compact metadata table at the top of `report.md` with run timestamp, version, config path, dataset, sample size, total audio duration, engines evaluated, and repository link while keeping the report to a single-page summary
- [x] Make `report.md` distinguish adapter/runtime failures from real benchmark scores so engine rows with `info.error` are not presented as normal `WER/CER = 1.000` results without a visible failure indicator

## Longer-term / stretch desires
- Add structured experiment definitions (train/validation splits)
- Add support for cloud/offload setups (if Apple Silicon isn’t enough)
- Add metric visualizations (plots) in report generation
- Add automated model download + validation hooks
