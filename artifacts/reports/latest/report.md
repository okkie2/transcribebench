# TranscribeBench Report

**Date:** 15 March 2026  
**Author:** Joost Okkinga  
**Repository:** https://github.com/okkie2/transcribebench

## Key Takeaways

- `mlx_whisper`, `faster_whisper_large` tied for the best WER at 0.017.
- `parakeet_mlx` was the fastest engine at 0.233s average transcription time.
- `mlx_whisper` offered the best balance between speed and accuracy among the successful runs.
- `faster_whisper_large` was notably slower at 6.579s average time per sample.
- `apple_dictation` was the weakest successful engine on accuracy with WER 0.173.
- This run used only 5 samples, so the quality and timing results are indicative rather than stable.

## Benchmark Environment

| Field | Value |
| --- | --- |
| Timestamp | 2026-03-15T21:55:16.509312Z |
| Version | 0.1.0 |
| Hardware | arm64 |
| OS | Darwin 25.3.0 |
| Language | nl |
| Dataset | Mozilla Common Voice (nl) |
| Samples | 5 |
| Total audio | 25s |
| Failures | 0 |
| Config | config/default.yaml |

## Benchmark Results

| engine | model | status | WER | CER | time_seconds |
| --- | --- | ---: | ---: | ---: | ---: |
| apple_dictation | nl-NL | ok | 0.173 | 0.069 | 0.274 |
| mlx_whisper | mlx-community/whisper-large-v3-turbo | ok | 0.017 | 0.005 | 0.765 |
| faster_whisper | guillaumekln/faster-whisper-small | ok | 0.120 | 0.031 | 1.835 |
| faster_whisper_large | guillaumekln/faster-whisper-large-v2 | ok | 0.017 | 0.005 | 6.579 |
| whisper_cpp | large-v1 | ok | 0.033 | 0.028 | 1.864 |
| parakeet_mlx | mlx-community/parakeet-tdt-0.6b-v3 | ok | 0.033 | 0.010 | 0.233 |

## Speed vs Accuracy

- `parakeet_mlx` leads on speed at 0.233s per sample, while `mlx_whisper` leads on accuracy at WER 0.017.
- If throughput matters most, start with `parakeet_mlx`. If transcription quality matters most, start with `mlx_whisper`.
- `faster_whisper_large` is the slowest successful engine in this run, so it needs a clear quality advantage to justify its runtime cost.

## Metrics

- WER = Word Error Rate.
- CER = Character Error Rate.
- Lower is better for both metrics.

## Notes and Limitations

- This report summarizes a run of 5 samples.
- Adapter or runtime errors are shown in the `status` column and should not be read as normal quality results.
- Small sample counts are indicative only and should not be treated as stable rankings.

Detailed results are available in `results.csv` and `results.json`.
