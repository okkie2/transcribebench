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
