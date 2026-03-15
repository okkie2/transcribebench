# TODO / Roadmap (v1)

## Immediate next work (v1)
- [ ] Implement Common Voice subset downloader and deterministic sampling
- [ ] Implement basic transcription runners calling each engine adapter
- [ ] Implement WER/CER calculation and validation against known ground truth
- [ ] Persist raw engine transcripts and per-file timing data
- [ ] Flesh out report generator (Markdown + JSON + CSV)
- [ ] Add CI / test coverage for critical core logic

## v1.x improvements
- Add optional GPU/Metal performance tuning knobs per engine
- Add model selection abstraction (large models only, but allow model overrides)
- Add reproducible Docker/conda environment spec
- Add support for multiple languages (after Dutch baseline is stable)
- Add optional per-engine warmup and caching (model load times)

## Longer-term / stretch desires
- Add structured experiment definitions (train/validation splits)
- Add support for cloud/offload setups (if Apple Silicon isn’t enough)
- Add metric visualizations (plots) in report generation
