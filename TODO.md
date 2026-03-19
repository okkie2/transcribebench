# TODO / Roadmap

`TODO.md` is forward-looking only. Completed work belongs in `CHANGELOG.md`, not here.

## Current baseline
Current release baseline: `v1.0.0`

## Target v1.0.1
- Define and document a lightweight major/minor/patch versioning policy for the repository
- Add `CHANGELOG.md` with versioned release entries only
- Add `RELEASE_NOTES.md` with a small per-release summary template
- Improve CLI transparency when downloading speech models by printing a clear pre-download message with engine, model name, and approximate size when known

## Target v1.1.0
- Add benchmark configuration profiles for small, medium, and large runs
- Add a model selection abstraction so benchmark configs can describe intent while still allowing explicit model overrides
- Add optional per-engine warmup and caching handling so repeated runs are easier to compare fairly
- Evaluate whether additional engine adapters such as `distil-large-v3`, `nvidia/parakeet-ctc-1.1b`, and `facebook/mms-1b-all` are still worth adding

## Backlog
- Add optional GPU/Metal performance tuning knobs per engine
- Add reproducible Docker or conda environment definitions
- Add support for multiple languages after the Dutch baseline workflow is stable
- Add structured experiment definitions such as train and validation splits
- Add metric visualizations to report generation
- Add automated model download and validation hooks
- Add support for cloud or offload benchmark setups if local Apple Silicon capacity becomes a limiting factor
