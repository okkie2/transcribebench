# TranscribeBench Report

**Date:** 18 March 2026  
**Author:** Joost Okkinga  
**Repository:** https://github.com/okkie2/transcribebench

## Key Takeaways

- `mlx_whisper` was the most accurate engine in this run with WER 0.069 and CER 0.026.
- `apple_dictation` was the fastest engine at 0.360s average transcription time.
- `mlx_whisper` offered the best balance between speed and accuracy among the successful runs.
- `apple_dictation` was the weakest successful engine on accuracy with WER 0.212.

## Benchmark Environment

| Field | Value |
| --- | --- |
| Timestamp | 2026-03-18T21:01:14.677911Z |
| Version | 0.1.0 |
| Hardware | arm64 |
| OS | Darwin 25.3.0 |
| Language | nl |
| Dataset | Mozilla Common Voice (nl) |
| Samples | 150 |
| Total audio | 10m 48s |
| Failures | 0 |
| Config | config/default.yaml |

## Benchmark Results

| engine | model | status | WER | CER | time_seconds |
| --- | --- | ---: | ---: | ---: | ---: |
| apple_dictation | nl-NL | ok | 0.212 | 0.067 | 0.360 |
| mlx_whisper | mlx-community/whisper-large-v3-turbo | ok | 0.069 | 0.026 | 0.574 |

## Speed vs Accuracy

- `apple_dictation` leads on speed at 0.360s per sample, while `mlx_whisper` leads on accuracy at WER 0.069.
- If throughput matters most, start with `apple_dictation`. If transcription quality matters most, start with `mlx_whisper`.
- `mlx_whisper` is the slowest successful engine in this run, so it needs a clear quality advantage to justify its runtime cost.

## Metrics

- WER = Word Error Rate.
- CER = Character Error Rate.
- Lower is better for both metrics.

## Notes and Limitations

- This report summarizes a run of 150 samples.
- Adapter or runtime errors are shown in the `status` column and should not be read as normal quality results.
- Small sample counts are indicative only and should not be treated as stable rankings.

Detailed results are available in `results.csv` and `results.json`.
