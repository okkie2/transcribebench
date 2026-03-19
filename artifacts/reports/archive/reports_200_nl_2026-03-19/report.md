# TranscribeBench Report

**Date:** 19 March 2026  
**Author:** Joost Okkinga  
**Repository:** https://github.com/okkie2/transcribebench

## Key Takeaways

- `parakeet_mlx` was the most accurate engine in this run with WER 0.049 and CER 0.014.
- `parakeet_mlx` was the fastest engine at 0.168s average transcription time.
- `parakeet_mlx` delivered the strongest overall balance of speed and accuracy in this run.
- `faster_whisper_large` was notably slower at 6.281s average time per sample.
- `apple_dictation` was the weakest successful engine on accuracy with WER 0.209.

## Benchmark Environment

| Field | Value |
| --- | --- |
| Timestamp | 2026-03-19T11:53:01.360806Z |
| Version | 0.1.0 |
| Hardware | arm64 |
| OS | Darwin 25.3.0 |
| Language | nl |
| Dataset | Mozilla Common Voice (nl) |
| Samples | 200 |
| Total audio | 14m 18s |
| Failures | 0 |
| Config | config/default.yaml |

## Benchmark Results

| engine | model | status | WER | CER | time_seconds |
| --- | --- | ---: | ---: | ---: | ---: |
| apple_dictation | nl-NL | ok | 0.209 | 0.066 | 0.341 |
| mlx_whisper | mlx-community/whisper-large-v3-turbo | ok | 0.073 | 0.030 | 0.486 |
| faster_whisper | guillaumekln/faster-whisper-small | ok | 0.141 | 0.055 | 1.724 |
| faster_whisper_large | guillaumekln/faster-whisper-large-v2 | ok | 0.072 | 0.033 | 6.281 |
| whisper_cpp | large-v1 | ok | 0.086 | 0.033 | 1.941 |
| parakeet_mlx | mlx-community/parakeet-tdt-0.6b-v3 | ok | 0.049 | 0.014 | 0.168 |

## Speed vs Accuracy

- `parakeet_mlx` leads on speed at 0.168s per sample, while `parakeet_mlx` leads on accuracy at WER 0.049.
- `parakeet_mlx` currently leads on both speed and accuracy in this benchmark.
- `faster_whisper_large` is the slowest successful engine in this run, so it needs a clear quality advantage to justify its runtime cost.

## Metrics

- WER = Word Error Rate.
- CER = Character Error Rate.
- Lower is better for both metrics.

## Notes and Limitations

- This report summarizes a run of 200 samples.
- Adapter or runtime errors are shown in the `status` column and should not be read as normal quality results.
- Small sample counts are indicative only and should not be treated as stable rankings.

Detailed results are available in `results.csv` and `results.json`.
