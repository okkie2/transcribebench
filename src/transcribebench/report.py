"""Report generation for benchmark results."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any, Dict, List


class Reporter:
    @staticmethod
    def write_reports(results: Dict[str, Any], out_dir: Path) -> None:
        Reporter._write_markdown(results, out_dir / "report.md")
        Reporter._write_csv(results, out_dir / "results.csv")

    @staticmethod
    def _write_markdown(results: Dict[str, Any], path: Path) -> None:
        lines: List[str] = []
        lines.append("# TranscribeBench Report\n")
        lines.append("## Summary\n")

        metrics = results.get("metrics", {})
        lines.append(f"- Total samples: {metrics.get('total_samples', 0)}")
        lines.append(f"- Engines: {', '.join(metrics.get('engines', []))}")
        lines.append(f"- Failures: {metrics.get('failures', 0)}")
        lines.append("\n---\n")

        lines.append("## Per-engine overview\n")
        per_engine = metrics.get("per_engine", {})
        if per_engine:
            lines.append("| Engine | Avg WER | Avg CER | Avg time (s) | Avg RTF |")
            lines.append("| --- | ---: | ---: | ---: | ---: |")
            for engine_name, stats in per_engine.items():
                avg_wer = float(stats.get("avg_wer", 0.0))
                avg_cer = float(stats.get("avg_cer", 0.0))
                avg_time = float(stats.get("avg_transcription_time_seconds", 0.0))
                avg_rtf = stats.get("avg_rtf")
                rtf_str = f"{float(avg_rtf):.3f}" if avg_rtf is not None else "n/a"
                lines.append(
                    f"| {engine_name} | {avg_wer:.3f} | {avg_cer:.3f} | {avg_time:.3f} | {rtf_str} |"
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
