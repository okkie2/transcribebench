"""Benchmark runner orchestrates dataset, engines, and result collection."""

from __future__ import annotations

import dataclasses
import json
import pathlib
import time
from collections import defaultdict
from typing import List

from .config import Config
from .dataset.common_voice import CommonVoiceProvider, CommonVoiceSample
from .engines import EngineAdapter, EngineResult
from .report import Reporter


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

    def __init__(self, config: Config, engines: list[EngineAdapter]):
        self.config = config
        self.engines = engines
        self.dataset_provider = CommonVoiceProvider(config.output.dataset_cache)

    def run(self) -> dict:
        """Run benchmark end-to-end and return a structured results dict."""
        samples = self.dataset_provider.fetch(
            language=self.config.language,
            size=self.config.dataset.sample_size,
            seed=self.config.dataset.seed,
            url=self.config.dataset.url,
        )

        results: list[dict] = []
        failures = 0

        for sample in samples:
            for engine in self.engines:
                start = time.time()
                try:
                    result = engine.transcribe(
                        audio_path=sample.audio_path,
                        model=getattr(self.config.engines, engine.name).model,
                        language=self.config.language,
                    )
                except Exception as e:
                    failures += 1
                    result = EngineResult(
                        engine=engine.name,
                        sample_id=sample.id,
                        audio_path=sample.audio_path,
                        transcript="",
                        elapsed_seconds=time.time() - start,
                        real_time_factor=None,
                        info={"error": str(e)},
                    )

                wer = _simple_wer(sample.transcript, result.transcript)
                cer = _simple_cer(sample.transcript, result.transcript)

                results.append(
                    {
                        **dataclasses.asdict(result),
                        "rtf": result.real_time_factor,
                        "reference": sample.transcript,
                        "wer": wer,
                        "cer": cer,
                    }
                )

        per_engine: dict[str, dict[str, float | int | None]] = {}
        by_engine: dict[str, list[dict]] = defaultdict(list)
        for row in results:
            by_engine[row["engine"]].append(row)

        for engine_name, rows in by_engine.items():
            count = len(rows)
            avg_wer = sum(float(r["wer"]) for r in rows) / max(1, count)
            avg_cer = sum(float(r["cer"]) for r in rows) / max(1, count)
            avg_elapsed = sum(float(r["elapsed_seconds"]) for r in rows) / max(1, count)

            rtfs = [float(r["real_time_factor"]) for r in rows if r.get("real_time_factor") is not None]
            avg_rtf = (sum(rtfs) / len(rtfs)) if rtfs else None

            per_engine[engine_name] = {
                "count": count,
                "avg_wer": avg_wer,
                "avg_cer": avg_cer,
                "avg_transcription_time_seconds": avg_elapsed,
                "avg_rtf": avg_rtf,
            }

        metrics = {
            "total_samples": len(samples),
            "engines": [e.name for e in self.engines],
            "failures": failures,
            "per_engine": per_engine,
        }

        output = {
            "config": {
                "language": self.config.language,
                "dataset": dataclasses.asdict(self.config.dataset),
                "output": dataclasses.asdict(self.config.output),
                "engines": {
                    "mlx_whisper": dataclasses.asdict(self.config.engines.mlx_whisper),
                    "faster_whisper": dataclasses.asdict(self.config.engines.faster_whisper),
                    "faster_whisper_large": dataclasses.asdict(self.config.engines.faster_whisper_large),
                    "whisper_cpp": dataclasses.asdict(self.config.engines.whisper_cpp),
                    "parakeet_ctc_1_1b": dataclasses.asdict(self.config.engines.parakeet_ctc_1_1b),
                },
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
