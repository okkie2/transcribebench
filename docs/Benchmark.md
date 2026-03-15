# Benchmark Methodology

This page explains what a benchmark run does, how datasets are prepared, what an engine means in TranscribeBench, and how to interpret the generated outputs.

## What a benchmark run does

A benchmark run evaluates one or more engine/model pairs against the same fixed dataset subset.

At a high level, a run:

1. Loads the benchmark configuration from a YAML file in `config/`.
2. Refreshes or reuses a cached dataset subset for the configured language, sample size, seed, and dataset URL.
3. Executes each enabled engine/model pair on each sample audio file.
4. Captures the raw transcript, elapsed time, optional real-time factor, and any engine error information.
5. Compares each transcript with the reference transcript for that sample.
6. Aggregates metrics and writes machine-readable and human-readable outputs.

The benchmark runner currently executes samples sequentially for each enabled engine/model pair. Every engine is evaluated against the same sample set so the comparison remains fair.

## Engine concept

In this project, an **engine** is the runtime adapter responsible for loading a model and exposing a consistent transcription interface to the benchmark runner.

An engine is not the same thing as a model:

- The **engine** is the integration/runtime layer.
- The **model** is the actual neural network weights loaded by that engine.

Examples of engines in this repository:

- `apple_dictation` for Apple's native `DictationTranscriber` on macOS 26+
- `apple_speech` for Apple's native SpeechAnalyzer + SpeechTranscriber APIs on macOS 26+
- `mlx_whisper` for Whisper-family models running through MLX
- `faster_whisper` for CTranslate2-based Whisper inference
- `whisper_cpp` for `whisper.cpp`
- `parakeet_mlx` for Parakeet models running on MLX

An engine adapter is expected to:

- check whether its runtime requirements are installed
- load the requested model
- transcribe a single audio file
- return results in the common `EngineResult` shape used by the runner

This separation lets the benchmark framework compare different runtimes while keeping the runner logic generic.

For Apple-native transcription there are currently two distinct runtime paths:

- `apple_speech` uses `SpeechTranscriber`
- `apple_dictation` uses `DictationTranscriber`

These do not have identical locale support. On this machine, `DictationTranscriber` supports Dutch (`nl-NL`) while `SpeechTranscriber` does not.

## How transcripts are compared

Each dataset sample has:

- an audio file path
- a sample identifier
- a reference transcript

For every sample, the runner asks each enabled engine/model pair to produce a transcript from the audio file. That transcript is then compared with the reference transcript stored in the dataset metadata.

The benchmark stores both the engine output and the reference text in `results.json` and `results.csv`, so individual mismatches can be inspected after the run.

## How WER and CER are computed

TranscribeBench currently computes accuracy with straightforward Levenshtein-distance metrics:

- **WER (Word Error Rate)** compares tokenized words
- **CER (Character Error Rate)** compares individual characters

Both metrics are computed as:

`edit_distance(reference, hypothesis) / len(reference)`

Current implementation details:

- WER tokenizes on whitespace
- CER operates on stripped character sequences
- lower values are better
- `0.000` means an exact match
- `1.000` means the number of edits equals the reference length

These metrics are intentionally simple and deterministic. They are useful for consistent relative comparisons across engine/model pairs, even though they do not yet include advanced normalization such as punctuation folding or case normalization.

## Dataset structure

The default dataset provider is a deterministic subset builder for Mozilla Common Voice.

Inside the dataset cache, a language-specific dataset looks like this:

```text
.cache/datasets/
  nl/
    common_voice.tar.gz
    metadata.json
    raw/
    audio/
      nl-0000.mp3
      nl-0001.mp3
      ...
```

Important files and directories:

- `audio/` contains the copied benchmark audio files for the selected subset
- `metadata.json` stores dataset metadata and the sample list
- `raw/` contains the extracted source archive while preparing the subset
- `common_voice.tar.gz` is the cached source archive used to build the subset

Each sample record in `metadata.json` includes:

- `id`
- `audio_path`
- `transcript`

That metadata is what the benchmark runner uses to load the dataset and compare engine output against reference transcripts.

## Dataset loading and caching

The dataset provider uses the configured cache directory and language as its working location.

When a benchmark starts, the provider:

1. Checks whether `metadata.json` already exists.
2. Verifies that the cached subset matches the requested `sample_size` and `seed`.
3. Verifies that the referenced audio files still exist and are non-empty.
4. Reuses the cache if it matches.
5. Otherwise rebuilds the subset from the configured dataset archive.

If the configured archive cannot be downloaded, the provider can fall back to a synthetic dataset for development purposes. That synthetic path is primarily a resilience mechanism and should not be used for meaningful engine comparisons.

## Dataset reproducibility

Reproducibility is a core part of the project.

Benchmark results are only useful if different engines are evaluated on the same fixed subset. TranscribeBench therefore defines a dataset subset by the combination of:

- language
- dataset source URL
- sample size
- random seed

The dataset provider uses a deterministic random generator seeded from configuration, shuffles the available dataset entries, and selects the first `N` items after shuffling. That means the same configuration should produce the same subset again when rebuilt from the same source archive.

This matters because benchmark scores can change significantly if:

- speakers change
- audio quality changes
- accents or recording conditions change
- the dataset version changes

Benchmark results therefore reference dataset-defining inputs in the run output:

- `config.dataset.sample_size`
- `config.dataset.seed`
- `config.dataset.url`
- `run.language`

Together, these fields make it easier to understand what was actually benchmarked and whether two runs are comparable.

## Dataset sources

The default source is **Mozilla Common Voice**, an open speech dataset project with community-contributed voice recordings and transcripts.

Common Voice is useful here because it provides:

- real speech recordings
- aligned reference text
- public dataset releases
- language coverage beyond English

Project links:

- Common Voice project: <https://commonvoice.mozilla.org/>
- Dataset repository information: <https://huggingface.co/datasets/mozilla-foundation/common_voice_17_0>

You can also point TranscribeBench at a different archive URL or local file path through configuration when you want to benchmark another release or a locally stored dataset archive.

## Benchmark outputs

Each benchmark run produces three main outputs:

- `artifacts/results/.../results.json`
- `artifacts/reports/.../results.csv`
- `artifacts/reports/.../report.md`

### `results.json`

This is the canonical machine-readable run artifact. It contains:

- `run` metadata such as timestamp, config path, engines evaluated, dataset info, language, and sample size
- `config`, a snapshot of the effective benchmark configuration
- `metrics`, including total samples, failure count, and per-engine/model aggregate metrics
- `results`, the per-sample detailed rows

Each row in `results` includes fields such as:

- engine
- model
- sample identifier
- audio path
- transcript
- reference
- elapsed time
- optional real-time factor
- WER
- CER
- `info` for engine-specific details or errors

Use `results.json` when you need a complete, reproducible record of a benchmark run.

### `results.csv`

This is a flattened export of the detailed per-sample rows from `results.json`.

It is useful for:

- spreadsheet analysis
- plotting
- filtering by sample, engine, or model
- quick external inspection without writing a JSON parser

### `report.md`

This is the high-level human-readable summary.

It currently includes:

- total sample count
- engines evaluated
- failure count
- a per-engine/model summary table with average WER, average CER, and average transcription time

`report.md` is the fastest way to review a completed run, while `results.json` remains the source of truth for detailed inspection.

## How to interpret the metrics

Accuracy:

- lower WER is better
- lower CER is better
- a low CER with a higher WER often means word boundaries or a few entire words were wrong

Timing:

- `elapsed_seconds` is the wall-clock transcription time for a single sample
- `avg_transcription_time_seconds` is the average across samples for one engine/model pair
- `real_time_factor` is `transcription_time / audio_duration` when audio duration could be determined

Failure handling:

- `failures` counts rows where transcription raised an error or returned an error marker
- a row with an empty transcript and an `info.error` field usually means adapter or runtime failure rather than poor recognition quality

Because of that, a very poor WER/CER can mean either:

- the engine genuinely performed badly on the speech data, or
- the adapter/runtime failed and produced an empty transcript

Always inspect the `info` field in `results.json` when results look suspicious.

## Hardware context

Benchmark results are hardware-dependent.

The same engine and model can behave very differently depending on:

- CPU and GPU architecture
- available RAM
- storage speed
- model size
- dataset size

This repository is primarily tested on **Apple Silicon** machines and includes integrations that benefit from **MLX**, which is optimized for Apple Silicon GPUs. That means:

- MLX-based results are most representative on Apple Silicon
- larger models may require substantially more RAM and disk space
- timing comparisons should be interpreted within the context of the machine that produced them

When sharing benchmark numbers, include at least:

- machine type
- RAM
- Python version
- enabled engines/models
- dataset configuration

Without that context, timing results are difficult to compare across runs or across contributors.
