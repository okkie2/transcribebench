"""Configuration loading for TranscribeBench."""

from __future__ import annotations

import dataclasses
import pathlib
from typing import Any, Dict, Optional

import yaml


@dataclasses.dataclass(frozen=True)
class EngineConfig:
    enabled: bool = True
    # Default to a model that is publicly available and reasonable for benchmarking.
    model: str = "openai/whisper-small"


@dataclasses.dataclass(frozen=True)
class DatasetConfig:
    provider: str = "common_voice"
    sample_size: int = 50
    seed: int = 42
    # Optional download URL for the Common Voice archive (language-specific)
    url: str = "https://voice-prod-bundler.storage.googleapis.com/cv-corpus-14.0-2023-12-11/nl.tar.gz"


@dataclasses.dataclass(frozen=True)
class OutputConfig:
    results_dir: str = "runs"
    reports_dir: str = "reports"
    dataset_cache: str = "dataset_cache"


@dataclasses.dataclass(frozen=True)
class EnginesConfig:
    mlx_whisper: EngineConfig = EngineConfig()
    faster_whisper: EngineConfig = EngineConfig()
    faster_whisper_large: EngineConfig = EngineConfig()
    whisper_cpp: EngineConfig = EngineConfig()


@dataclasses.dataclass(frozen=True)
class Config:
    language: str = "nl"
    dataset: DatasetConfig = DatasetConfig()
    output: OutputConfig = OutputConfig()
    engines: EnginesConfig = EnginesConfig()

    @classmethod
    def load(cls, path: str | pathlib.Path = "config.yaml") -> "Config":
        path = pathlib.Path(path)
        with path.open("r", encoding="utf-8") as f:
            raw = yaml.safe_load(f) or {}

        # Simple merge of defaults + config file values.
        language = raw.get("language", cls().language)
        dataset_raw = raw.get("dataset", {})
        output_raw = raw.get("output", {})
        engines_raw: Dict[str, Any] = raw.get("engines", {})

        return cls(
            language=language,
            dataset=DatasetConfig(
                provider=dataset_raw.get("provider", cls().dataset.provider),
                sample_size=dataset_raw.get("sample_size", cls().dataset.sample_size),
                seed=dataset_raw.get("seed", cls().dataset.seed),
                url=dataset_raw.get("url", cls().dataset.url),
            ),
            output=OutputConfig(
                results_dir=output_raw.get("results_dir", cls().output.results_dir),
                reports_dir=output_raw.get("reports_dir", cls().output.reports_dir),
                dataset_cache=output_raw.get("dataset_cache", cls().output.dataset_cache),
            ),
            engines=EnginesConfig(
                mlx_whisper=EngineConfig(**(engines_raw.get("mlx_whisper", {}) or {})),
                faster_whisper=EngineConfig(**(engines_raw.get("faster_whisper", {}) or {})),
                faster_whisper_large=EngineConfig(**(engines_raw.get("faster_whisper_large", {}) or {})),
                whisper_cpp=EngineConfig(**(engines_raw.get("whisper_cpp", {}) or {})),
            ),
        )
