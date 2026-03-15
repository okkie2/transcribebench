from __future__ import annotations

from pathlib import Path

from transcribebench.report import Reporter


def test_report_marks_failed_engine_rows(tmp_path: Path) -> None:
    results = {
        "run": {
            "started_at_utc": "2026-03-15T21:34:00Z",
            "config_path": "config/default.yaml",
            "dataset_name": "Mozilla Common Voice (nl)",
            "sample_size": 3,
            "total_audio_seconds": 42.0,
            "os": "Darwin 26.3.1",
            "hardware": "arm64",
        },
        "config": {
            "language": "nl",
            "dataset": {"provider": "common_voice"},
        },
        "metrics": {
            "total_samples": 3,
            "engines": ["mlx_whisper", "parakeet_mlx"],
            "failures": 3,
            "per_engine_model": {
                "mlx_whisper::model": {
                    "engine": "mlx_whisper",
                    "model": "model",
                    "count": 3,
                    "failed_count": 0,
                    "avg_wer": 0.1,
                    "avg_cer": 0.02,
                    "avg_transcription_time_seconds": 0.5,
                    "avg_rtf": None,
                },
                "parakeet_mlx::model": {
                    "engine": "parakeet_mlx",
                    "model": "model",
                    "count": 3,
                    "failed_count": 3,
                    "avg_wer": 1.0,
                    "avg_cer": 1.0,
                    "avg_transcription_time_seconds": 0.8,
                    "avg_rtf": None,
                },
            },
        },
        "results": [],
    }

    out_dir = tmp_path / "report"
    out_dir.mkdir()
    Reporter.write_reports(results, out_dir)

    report = (out_dir / "report.md").read_text(encoding="utf-8")
    assert "# TranscribeBench Report" in report
    assert "**Author:** Joost Okkinga" in report
    assert "**Repository:** https://github.com/okkie2/transcribebench" in report
    assert "## Key Takeaways" in report
    assert "## Benchmark Environment" in report
    assert "| OS | Darwin 26.3.1 |" in report
    assert "| Hardware | arm64 |" in report
    assert "## Benchmark Results" in report
    assert "| engine | model | status | WER | CER | time_seconds |" in report
    assert "| mlx_whisper | model | ok | 0.100 | 0.020 | 0.500 |" in report
    assert "| parakeet_mlx | model | failed (3/3) | failed | failed | 0.800 |" in report
    assert "## Speed vs Accuracy" in report
    assert "## Metrics" in report
    assert "## Notes and Limitations" in report
    assert "Detailed results are available in `results.csv` and `results.json`." in report
