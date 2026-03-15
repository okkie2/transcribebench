"""Benchmark runner orchestrates dataset, engines, and result collection."""

from __future__ import annotations

import dataclasses
import json
import pathlib
import time
import os
import platform
import subprocess
from datetime import datetime, timezone
from collections import defaultdict
from typing import List, Optional

from .config import Config
from .dataset.common_voice import CommonVoiceProvider, CommonVoiceSample
from .engines import EngineAdapter, EngineResult
from .report import Reporter


def _audio_duration_seconds(path: str | pathlib.Path) -> Optional[float]:
    audio_path = pathlib.Path(path)

    try:
        import wave

        with wave.open(str(audio_path), "rb") as w:
            frames = w.getnframes()
            rate = w.getframerate()
            return frames / float(rate)
    except Exception:
        pass

    ffprobe = "ffprobe"
    try:
        proc = subprocess.run(
            [
                ffprobe,
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "default=noprint_wrappers=1:nokey=1",
                str(audio_path),
            ],
            capture_output=True,
            text=True,
        )
    except Exception:
        return None

    if proc.returncode != 0:
        return None

    try:
        return float((proc.stdout or "").strip())
    except ValueError:
        return None


def _simple_wer(ref: str, hyp: str) -> float:
    ref_tokens = ref.strip().split()
    hyp_tokens = hyp.strip().split()
    # Simple Levenshtein distance on token sequences
    n = len(ref_tokens)
    m = len(hyp_tokens)

    dp = [[0] * (m + 1) for _ in range(n + 1)]
    for i in range(1, n + 1):
        dp[i][0] = i
    for j in range(1, m + 1):
        dp[0][j] = j

    for i in range(1, n + 1):
        for j in range(1, m + 1):
            if ref_tokens[i - 1] == hyp_tokens[j - 1]:
                dp[i][j] = dp[i - 1][j - 1]
            else:
                dp[i][j] = 1 + min(dp[i - 1][j], dp[i][j - 1], dp[i - 1][j - 1])

    return dp[n][m] / max(1, n)


def _simple_cer(ref: str, hyp: str) -> float:
    ref_chars = list(ref.strip())
    hyp_chars = list(hyp.strip())
    n = len(ref_chars)
    m = len(hyp_chars)

    dp = [[0] * (m + 1) for _ in range(n + 1)]
    for i in range(1, n + 1):
        dp[i][0] = i
    for j in range(1, m + 1):
        dp[0][j] = j

    for i in range(1, n + 1):
        for j in range(1, m + 1):
            if ref_chars[i - 1] == hyp_chars[j - 1]:
                dp[i][j] = dp[i - 1][j - 1]
            else:
                dp[i][j] = 1 + min(dp[i - 1][j], dp[i][j - 1], dp[i - 1][j - 1])

    return dp[n][m] / max(1, n)


class BenchmarkRunner:
    """Runs a benchmark across engines and a dataset."""

    @dataclasses.dataclass(frozen=True)
    class RunTarget:
        adapter: EngineAdapter
        model: str

    def __init__(self, config: Config, targets: list["BenchmarkRunner.RunTarget"]):
        self.config = config
        self.targets = targets
        self.dataset_provider = CommonVoiceProvider(config.output.dataset_cache)

    def run(self) -> dict:
        """Run benchmark end-to-end and return a structured results dict."""
        run_started_at_utc = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        samples = self.dataset_provider.fetch(
            language=self.config.language,
            size=self.config.dataset.sample_size,
            seed=self.config.dataset.seed,
            url=self.config.dataset.url,
        )
        total_audio_seconds = sum(
            duration for sample in samples for duration in [_audio_duration_seconds(sample.audio_path)] if duration is not None
        )
        dataset_name = (
            f"Mozilla Common Voice ({self.config.language})"
            if self.config.dataset.provider == "common_voice"
            else f"{self.config.dataset.provider} ({self.config.language})"
        )

        results: list[dict] = []
        failures = 0
        debug_engine = os.environ.get("TRANSCRIBEBENCH_DEBUG_ENGINE")

        for sample in samples:
            for target in self.targets:
                start = time.time()
                try:
                    result = target.adapter.transcribe(
                        audio_path=sample.audio_path,
                        model=target.model,
                        language=self.config.language,
                    )
                except Exception as e:
                    failures += 1
                    result = EngineResult(
                        engine=target.adapter.engine_name,
                        model=target.model,
                        sample_id=sample.id,
                        audio_path=sample.audio_path,
                        transcript="",
                        elapsed_seconds=time.time() - start,
                        real_time_factor=None,
                        info={"error": str(e)},
                    )

                wer = _simple_wer(sample.transcript, result.transcript)
                cer = _simple_cer(sample.transcript, result.transcript)
                if isinstance(result.info, dict) and result.info.get("error"):
                    failures += 1

                if debug_engine and result.engine == debug_engine:
                    raw_output = result.transcript
                    normalized_output = result.transcript.strip()
                    print(f"[debug:{debug_engine}] audio={sample.audio_path}")
                    print(f"[debug:{debug_engine}] reference={sample.transcript!r}")
                    print(f"[debug:{debug_engine}] raw_output={raw_output!r}")
                    print(f"[debug:{debug_engine}] normalized_output={normalized_output!r}")
                    if isinstance(result.info, dict) and result.info.get("error"):
                        print(f"[debug:{debug_engine}] error={result.info.get('error')}")
                    print(f"[debug:{debug_engine}] wer={wer:.3f} cer={cer:.3f} elapsed={result.elapsed_seconds:.3f}")

                results.append(
                    {
                        **dataclasses.asdict(result),
                        "rtf": result.real_time_factor,
                        "reference": sample.transcript,
                        "wer": wer,
                        "cer": cer,
                    }
                )

        per_engine_model: dict[str, dict[str, float | int | None | str]] = {}
        by_engine_model: dict[tuple[str, str], list[dict]] = defaultdict(list)
        for row in results:
            by_engine_model[(row["engine"], row["model"])].append(row)

        for (engine_name, model_name), rows in by_engine_model.items():
            count = len(rows)
            failed_count = sum(1 for r in rows if isinstance(r.get("info"), dict) and r["info"].get("error"))
            avg_wer = sum(float(r["wer"]) for r in rows) / max(1, count)
            avg_cer = sum(float(r["cer"]) for r in rows) / max(1, count)
            avg_elapsed = sum(float(r["elapsed_seconds"]) for r in rows) / max(1, count)

            rtfs = [float(r["real_time_factor"]) for r in rows if r.get("real_time_factor") is not None]
            avg_rtf = (sum(rtfs) / len(rtfs)) if rtfs else None

            per_engine_model[f"{engine_name}::{model_name}"] = {
                "engine": engine_name,
                "model": model_name,
                "count": count,
                "failed_count": failed_count,
                "avg_wer": avg_wer,
                "avg_cer": avg_cer,
                "avg_transcription_time_seconds": avg_elapsed,
                "avg_rtf": avg_rtf,
            }

        metrics = {
            "total_samples": len(samples),
            "engines": [t.adapter.engine_name for t in self.targets],
            "failures": failures,
            "per_engine_model": per_engine_model,
        }

        output = {
            "run": {
                "started_at_utc": run_started_at_utc,
                "dataset_name": dataset_name,
                "sample_size": self.config.dataset.sample_size,
                "total_audio_seconds": total_audio_seconds,
                "os": f"{platform.system()} {platform.release()}",
                "hardware": platform.machine(),
            },
            "config": {
                "language": self.config.language,
                "dataset": dataclasses.asdict(self.config.dataset),
                "output": dataclasses.asdict(self.config.output),
                "engines": [dataclasses.asdict(e) for e in self.config.engines],
            },
            "metrics": metrics,
            "results": results,
        }

        return output

    def save_results(self, results: dict) -> None:
        results_dir = pathlib.Path(self.config.output.results_dir)
        reports_dir = pathlib.Path(self.config.output.reports_dir)

        results_dir.mkdir(parents=True, exist_ok=True)
        reports_dir.mkdir(parents=True, exist_ok=True)

        json_path = results_dir / "results.json"
        with json_path.open("w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)

        Reporter.write_reports(results, reports_dir)
