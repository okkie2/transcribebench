"""Report generation for benchmark results."""

from __future__ import annotations

import csv
import json
import importlib.metadata
from pathlib import Path
from typing import Any, Dict, List


class Reporter:
    REPO_URL = "https://github.com/okkie2/transcribebench"

    @staticmethod
    def write_reports(results: Dict[str, Any], out_dir: Path) -> None:
        Reporter._write_markdown(results, out_dir / "report.md")
        Reporter._write_csv(results, out_dir / "results.csv")

    @staticmethod
    def _resolve_version() -> str:
        try:
            return importlib.metadata.version("transcribebench")
        except Exception:
            pyproject_path = Path(__file__).resolve().parents[2] / "pyproject.toml"
            try:
                for line in pyproject_path.read_text(encoding="utf-8").splitlines():
                    if line.strip().startswith("version = "):
                        return line.split("=", 1)[1].strip().strip('"').strip("'")
            except Exception:
                pass
        return "unknown"

    @staticmethod
    def _format_duration(seconds: Any) -> str:
        try:
            total_seconds = int(round(float(seconds)))
        except Exception:
            return "unknown"

        hours, remainder = divmod(total_seconds, 3600)
        minutes, secs = divmod(remainder, 60)
        if hours > 0:
            return f"{hours}h {minutes}m {secs}s"
        if minutes > 0:
            return f"{minutes}m {secs}s"
        return f"{secs}s"

    @staticmethod
    def _write_markdown(results: Dict[str, Any], path: Path) -> None:
        lines: List[str] = []
        lines.append("# TranscribeBench Report\n")
        lines.append("## Benchmark metadata\n")
        run = results.get("run", {})
        config = results.get("config", {})
        metrics = results.get("metrics", {})
        metadata_rows = [
            ("Timestamp", str(run.get("started_at_utc", "unknown"))),
            ("Version", Reporter._resolve_version()),
            ("Config", str(run.get("config_path", "unknown"))),
            ("Dataset", str(run.get("dataset_name", f"{config.get('dataset', {}).get('provider', 'unknown')} ({config.get('language', 'unknown')})"))),
            ("Samples", str(run.get("sample_size", metrics.get("total_samples", 0)))),
            ("Total audio", Reporter._format_duration(run.get("total_audio_seconds"))),
            ("Engines", ", ".join(metrics.get("engines", [])) or "unknown"),
            ("Repo", Reporter.REPO_URL),
        ]
        lines.append("| Field | Value |")
        lines.append("| --- | --- |")
        for field, value in metadata_rows:
            lines.append(f"| {field} | {value} |")
        lines.append("\n---\n")

        lines.append("## Per engine/model overview\n")
        per_engine_model = metrics.get("per_engine_model", {})
        if per_engine_model:
            lines.append("| engine | model | WER | CER | time_seconds |")
            lines.append("| --- | --- | ---: | ---: | ---: |")
            for _, stats in per_engine_model.items():
                engine_name = str(stats.get("engine", ""))
                model_name = str(stats.get("model", ""))
                avg_wer = float(stats.get("avg_wer", 0.0))
                avg_cer = float(stats.get("avg_cer", 0.0))
                avg_time = float(stats.get("avg_transcription_time_seconds", 0.0))
                lines.append(
                    f"| {engine_name} | {model_name} | {avg_wer:.3f} | {avg_cer:.3f} | {avg_time:.3f} |"
                )
            lines.append("")
        lines.append("(Detailed results are available in `results.csv` and `results.json`.)\n")

        path.write_text("\n".join(lines), encoding="utf-8")

    @staticmethod
    def _write_csv(results: Dict[str, Any], path: Path) -> None:
        rows = results.get("results", [])
        if not rows:
            path.write_text("", encoding="utf-8")
            return

        fieldnames = list(rows[0].keys())
        with path.open("w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for row in rows:
                writer.writerow(row)
