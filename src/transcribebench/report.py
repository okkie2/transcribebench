"""Report generation for benchmark results."""

from __future__ import annotations

import csv
import importlib.metadata
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List


class Reporter:
    AUTHOR = "Joost Okkinga"
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
    def _format_report_date(timestamp: Any) -> str:
        if not timestamp:
            return "unknown"
        try:
            dt = datetime.fromisoformat(str(timestamp).replace("Z", "+00:00"))
            return dt.strftime("%d %B %Y")
        except Exception:
            return str(timestamp)

    @staticmethod
    def _markdown_table(headers: list[str], rows: list[list[str]]) -> list[str]:
        lines = [
            "| " + " | ".join(headers) + " |",
            "| " + " | ".join("---" if i < 2 else "---:" for i in range(len(headers))) + " |",
        ]
        for row in rows:
            lines.append("| " + " | ".join(row) + " |")
        return lines

    @staticmethod
    def _environment_rows(results: Dict[str, Any]) -> list[list[str]]:
        run = results.get("run", {})
        config = results.get("config", {})
        metrics = results.get("metrics", {})
        dataset_cfg = config.get("dataset", {})
        rows = [
            ["Timestamp", str(run.get("started_at_utc", "unknown"))],
            ["Version", Reporter._resolve_version()],
            ["Hardware", str(run.get("hardware", "unknown"))],
            ["OS", str(run.get("os", "unknown"))],
            ["Language", str(run.get("language", config.get("language", "unknown")))],
            ["Dataset", str(run.get("dataset_name", f"{dataset_cfg.get('provider', 'unknown')} ({config.get('language', 'unknown')})"))],
            ["Samples", str(run.get("sample_size", metrics.get("total_samples", 0)))],
            ["Total audio", Reporter._format_duration(run.get("total_audio_seconds"))],
            ["Failures", str(metrics.get("failures", 0))],
            ["Config", str(run.get("config_path", "unknown"))],
        ]
        return [[field, value] for field, value in rows if value not in {"", "unknown"} or field in {"Machine", "OS", "Config"}]

    @staticmethod
    def _result_rows(results: Dict[str, Any]) -> list[dict[str, Any]]:
        per_engine_model = results.get("metrics", {}).get("per_engine_model", {})
        rows: list[dict[str, Any]] = []
        for stats in per_engine_model.values():
            count = int(stats.get("count", 0))
            failed_count = int(stats.get("failed_count", 0))
            if failed_count == 0:
                status = "ok"
                wer_value = f"{float(stats.get('avg_wer', 0.0)):.3f}"
                cer_value = f"{float(stats.get('avg_cer', 0.0)):.3f}"
            elif failed_count >= count > 0:
                status = f"failed ({failed_count}/{count})"
                wer_value = "failed"
                cer_value = "failed"
            else:
                status = f"partial ({failed_count}/{count})"
                wer_value = f"{float(stats.get('avg_wer', 0.0)):.3f}"
                cer_value = f"{float(stats.get('avg_cer', 0.0)):.3f}"

            rows.append(
                {
                    "engine": str(stats.get("engine", "")),
                    "model": str(stats.get("model", "")),
                    "status": status,
                    "wer": float(stats.get("avg_wer", 0.0)),
                    "cer": float(stats.get("avg_cer", 0.0)),
                    "time_seconds": float(stats.get("avg_transcription_time_seconds", 0.0)),
                    "wer_display": wer_value,
                    "cer_display": cer_value,
                    "failed_count": failed_count,
                    "count": count,
                }
            )
        return rows

    @staticmethod
    def _key_takeaways(results: Dict[str, Any], rows: list[dict[str, Any]]) -> list[str]:
        metrics = results.get("metrics", {})
        total_samples = int(metrics.get("total_samples", 0))
        successful_rows = [row for row in rows if row["failed_count"] == 0]
        bullets: list[str] = []

        if successful_rows:
            fastest = min(successful_rows, key=lambda row: row["time_seconds"])
            lowest_wer = min(successful_rows, key=lambda row: row["wer"])["wer"]
            most_accurate = [row for row in successful_rows if abs(row["wer"] - lowest_wer) < 1e-12]
            balance = min(successful_rows, key=lambda row: (row["wer"], row["time_seconds"]))

            if len(most_accurate) == 1:
                winner = most_accurate[0]
                bullets.append(
                    f"`{winner['engine']}` was the most accurate engine in this run with WER {winner['wer_display']} and CER {winner['cer_display']}."
                )
            else:
                names = ", ".join(f"`{row['engine']}`" for row in most_accurate)
                bullets.append(f"{names} tied for the best WER at {lowest_wer:.3f}.")

            bullets.append(
                f"`{fastest['engine']}` was the fastest engine at {fastest['time_seconds']:.3f}s average transcription time."
            )

            if balance["engine"] == fastest["engine"] and balance["engine"] in {row["engine"] for row in most_accurate}:
                bullets.append(f"`{balance['engine']}` delivered the strongest overall balance of speed and accuracy in this run.")
            else:
                bullets.append(
                    f"`{balance['engine']}` offered the best balance between speed and accuracy among the successful runs."
                )

            slowest = max(successful_rows, key=lambda row: row["time_seconds"])
            weakest = max(successful_rows, key=lambda row: (row["wer"], row["cer"]))
            if slowest["engine"] != balance["engine"]:
                bullets.append(
                    f"`{slowest['engine']}` was notably slower at {slowest['time_seconds']:.3f}s average time per sample."
                )
            if weakest["engine"] not in {row["engine"] for row in most_accurate}:
                bullets.append(
                    f"`{weakest['engine']}` was the weakest successful engine on accuracy with WER {weakest['wer_display']}."
                )

        partial_or_failed = [row for row in rows if row["failed_count"] > 0]
        if partial_or_failed:
            affected = ", ".join(
                f"`{row['engine']}` ({row['failed_count']}/{row['count']})" for row in partial_or_failed
            )
            bullets.append(f"Some engines did not complete cleanly for every sample: {affected}.")

        if total_samples and total_samples <= 10:
            bullets.append(f"This run used only {total_samples} samples, so the quality and timing results are indicative rather than stable.")

        return bullets

    @staticmethod
    def _speed_vs_accuracy(rows: list[dict[str, Any]]) -> list[str]:
        successful_rows = [row for row in rows if row["failed_count"] == 0]
        if not successful_rows:
            return ["No fully successful engine runs were available for a clean speed-versus-accuracy comparison."]

        fastest = min(successful_rows, key=lambda row: row["time_seconds"])
        most_accurate = min(successful_rows, key=lambda row: (row["wer"], row["cer"]))
        tradeoffs: list[str] = []
        tradeoffs.append(
            f"`{fastest['engine']}` leads on speed at {fastest['time_seconds']:.3f}s per sample, while `{most_accurate['engine']}` leads on accuracy at WER {most_accurate['wer_display']}."
        )

        if fastest["engine"] != most_accurate["engine"]:
            tradeoffs.append(
                f"If throughput matters most, start with `{fastest['engine']}`. If transcription quality matters most, start with `{most_accurate['engine']}`."
            )
        else:
            tradeoffs.append(f"`{fastest['engine']}` currently leads on both speed and accuracy in this benchmark.")

        slowest = max(successful_rows, key=lambda row: row["time_seconds"])
        if slowest["engine"] != fastest["engine"]:
            tradeoffs.append(
                f"`{slowest['engine']}` is the slowest successful engine in this run, so it needs a clear quality advantage to justify its runtime cost."
            )
        return tradeoffs

    @staticmethod
    def _write_markdown(results: Dict[str, Any], path: Path) -> None:
        lines: List[str] = []
        run = results.get("run", {})
        metrics = results.get("metrics", {})
        rows = Reporter._result_rows(results)

        lines.append("# TranscribeBench Report\n")
        lines.append(f"**Date:** {Reporter._format_report_date(run.get('started_at_utc'))}  ")
        lines.append(f"**Author:** {Reporter.AUTHOR}  ")
        lines.append(f"**Repository:** {Reporter.REPO_URL}\n")

        lines.append("## Key Takeaways\n")
        for bullet in Reporter._key_takeaways(results, rows):
            lines.append(f"- {bullet}")
        lines.append("")

        lines.append("## Benchmark Environment\n")
        lines.extend(Reporter._markdown_table(["Field", "Value"], Reporter._environment_rows(results)))
        lines.append("")

        lines.append("## Benchmark Results\n")
        if rows:
            table_rows = [
                [
                    row["engine"],
                    row["model"],
                    row["status"],
                    row["wer_display"],
                    row["cer_display"],
                    f"{row['time_seconds']:.3f}",
                ]
                for row in rows
            ]
            lines.extend(
                Reporter._markdown_table(
                    ["engine", "model", "status", "WER", "CER", "time_seconds"],
                    table_rows,
                )
            )
            lines.append("")

        lines.append("## Speed vs Accuracy\n")
        for bullet in Reporter._speed_vs_accuracy(rows):
            lines.append(f"- {bullet}")
        lines.append("")

        lines.append("## Metrics\n")
        lines.append("- WER = Word Error Rate.")
        lines.append("- CER = Character Error Rate.")
        lines.append("- Lower is better for both metrics.\n")

        lines.append("## Notes and Limitations\n")
        sample_count = run.get("sample_size", metrics.get("total_samples", 0))
        lines.append(f"- This report summarizes a run of {sample_count} samples.")
        lines.append("- Adapter or runtime errors are shown in the `status` column and should not be read as normal quality results.")
        lines.append("- Small sample counts are indicative only and should not be treated as stable rankings.\n")

        lines.append("Detailed results are available in `results.csv` and `results.json`.\n")

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
