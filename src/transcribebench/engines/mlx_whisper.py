"""Adapter for MLX Whisper (Metal) engine."""

from __future__ import annotations

import time
import wave
from importlib.util import find_spec
from pathlib import Path
from typing import List, Optional

from .base import EngineAdapter, EngineResult


def _audio_duration_seconds(path: str | Path) -> Optional[float]:
    try:
        with wave.open(str(path), "rb") as w:
            frames = w.getnframes()
            rate = w.getframerate()
            return frames / float(rate)
    except Exception:
        return None


class MlxWhisperEngine(EngineAdapter):
    def __init__(self) -> None:
        self._model_name: Optional[str] = None

    @property
    def engine_name(self) -> str:
        return "mlx_whisper"

    def check_requirements(self) -> List[str]:
        missing: List[str] = []
        # Import-spec checks only: avoid triggering MLX device init in menu availability checks.
        if find_spec("mlx") is None:
            missing.append("Install MLX: pip install mlx")
        if find_spec("mlx_whisper") is None:
            missing.append("Install mlx-whisper: pip install mlx-whisper")

        return missing

    def transcribe(self, audio_path: str | Path, model: str, language: str, **kwargs) -> EngineResult:
        start = time.time()
        audio_path = Path(audio_path)

        try:
            import mlx_whisper

            duration = _audio_duration_seconds(audio_path)
            out = mlx_whisper.transcribe(
                str(audio_path),
                path_or_hf_repo=model,
                # Pass language to the decoding options via kwargs.
                language=language,
                # Use minimal verbosity by default
                verbose=False,
                **kwargs,
            )

            transcript = str(out.get("text", "")).strip()
            elapsed = time.time() - start
            rtf = None
            if duration and duration > 0:
                rtf = elapsed / duration

            return EngineResult(
                engine=self.engine_name,
                model=model,
                sample_id=audio_path.stem,
                audio_path=str(audio_path),
                transcript=transcript,
                elapsed_seconds=elapsed,
                real_time_factor=rtf,
                info={"model": model, "language": language},
            )
        except Exception as e:
            elapsed = time.time() - start
            return EngineResult(
                engine=self.engine_name,
                model=model,
                sample_id=audio_path.stem,
                audio_path=str(audio_path),
                transcript="",
                elapsed_seconds=elapsed,
                real_time_factor=None,
                info={"error": str(e), "model": model, "language": language},
            )
