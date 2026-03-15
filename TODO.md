  # TODO / Roadmap (v1)

## Immediate next work (v1)
- [x] Implement Common Voice subset downloader and deterministic sampling
- [x] Implement basic transcription runners calling each engine adapter
- [x] Implement WER/CER calculation and validation against known ground truth
- [x] Persist raw engine transcripts and per-file timing data
- [x] Add RTF metric (`transcription_time / audio_duration`) per sample and per-engine report summary
- [x] Flesh out report generator (Markdown + JSON + CSV)
- [x] Add CI / test coverage for critical core logic

## v1.x improvements
- Add optional GPU/Metal performance tuning knobs per engine
- Add model selection abstraction (large models only, but allow model overrides)
- Add reproducible Docker/conda environment spec
- Add support for multiple languages (after Dutch baseline is stable)
- Add optional per-engine warmup and caching (model load times)
- Add `distil-large-v3`, `nvidia/parakeet-ctc-1.1b`, `facebook/mms-1b-all` adapters
- Add benchmark configuration profiles (small/medium/large runs)

## Longer-term / stretch desires
- Add structured experiment definitions (train/validation splits)
- Add support for cloud/offload setups (if Apple Silicon isn’t enough)
- Add metric visualizations (plots) in report generation
- Add automated model download + validation hooks
