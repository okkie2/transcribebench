"""Configuration loading for TranscribeBench."""

from __future__ import annotations

import dataclasses
import pathlib
from typing import Any, Dict, List

import yaml


@dataclasses.dataclass(frozen=True)
class EngineSpec:
    engine: str
    model: str
    enabled: bool = True


@dataclasses.dataclass(frozen=True)
class DatasetConfig:
    provider: str = "common_voice"
    sample_size: int = 50
    seed: int = 42
    # Optional download URL for the Common Voice archive (language-specific)
    url: str = "https://voice-prod-bundler.storage.googleapis.com/cv-corpus-14.0-2023-12-11/nl.tar.gz"


@dataclasses.dataclass(frozen=True)
class OutputConfig:
    results_dir: str = "artifacts/results/latest"
    reports_dir: str = "artifacts/reports/latest"
    dataset_cache: str = ".cache/datasets"


def _default_engines() -> list[EngineSpec]:
    return [
        EngineSpec(engine="apple_dictation", model="nl-NL", enabled=False),
        EngineSpec(engine="apple_speech", model="nl-NL", enabled=False),
        EngineSpec(engine="mlx_whisper", model="openai/whisper-small", enabled=True),
        EngineSpec(engine="faster_whisper", model="openai/whisper-small", enabled=True),
        EngineSpec(engine="faster_whisper_large", model="openai/whisper-large-v3", enabled=True),
        EngineSpec(engine="whisper_cpp", model="small", enabled=True),
        EngineSpec(engine="parakeet_mlx", model="mlx-community/parakeet-tdt-0.6b-v3", enabled=False),
    ]


@dataclasses.dataclass(frozen=True)
class Config:
    language: str = "nl"
    dataset: DatasetConfig = DatasetConfig()
    output: OutputConfig = OutputConfig()
    engines: list[EngineSpec] = dataclasses.field(default_factory=_default_engines)

    @classmethod
    def load(cls, path: str | pathlib.Path = "config/default.yaml") -> "Config":
        path = pathlib.Path(path)
        with path.open("r", encoding="utf-8") as f:
            raw = yaml.safe_load(f) or {}

        language = raw.get("language", cls().language)
        dataset_raw = raw.get("dataset", {})
        output_raw = raw.get("output", {})
        engines_raw = raw.get("engines")

        engines = cls._parse_engines(engines_raw)

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
            engines=engines,
        )

    @staticmethod
    def _parse_engines(engines_raw: Any) -> list[EngineSpec]:
        if isinstance(engines_raw, list):
            parsed: list[EngineSpec] = []
            for item in engines_raw:
                if not isinstance(item, dict):
                    continue
                engine = item.get("engine")
                model = item.get("model")
                if not engine or not model:
                    continue
                parsed.append(
                    EngineSpec(
                        engine=str(engine),
                        model=str(model),
                        enabled=bool(item.get("enabled", True)),
                    )
                )
            return parsed or _default_engines()

        # Backward compatibility with the old mapping format:
        # engines:
        #   mlx_whisper: { enabled: true, model: ... }
        if isinstance(engines_raw, dict):
            legacy_to_engine = {
                "apple_dictation": "apple_dictation",
                "apple_speech": "apple_speech",
                "mlx_whisper": "mlx_whisper",
                "faster_whisper": "faster_whisper",
                "faster_whisper_large": "faster_whisper_large",
                "whisper_cpp": "whisper_cpp",
                "parakeet_ctc_1_1b": "parakeet_mlx",
                "nemo_ctc": "parakeet_mlx",
                "parakeet_mlx": "parakeet_mlx",
            }
            parsed: list[EngineSpec] = []
            for key, value in engines_raw.items():
                if key not in legacy_to_engine:
                    continue
                cfg = value or {}
                if not isinstance(cfg, dict):
                    continue
                model = cfg.get("model")
                if not model:
                    continue
                parsed.append(
                    EngineSpec(
                        engine=legacy_to_engine[key],
                        model=str(model),
                        enabled=bool(cfg.get("enabled", True)),
                    )
                )
            return parsed or _default_engines()

        return _default_engines()

    def enabled_engines(self) -> list[EngineSpec]:
        return [e for e in self.engines if e.enabled]
