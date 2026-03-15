"""Adapter for Parakeet models running on Apple Silicon via MLX."""

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


class ParakeetMlxEngine(EngineAdapter):
    """Engine adapter for Parakeet models on MLX."""

    def __init__(self) -> None:
        self._model = None
        self._model_name: Optional[str] = None
        self._module = None

    @property
    def engine_name(self) -> str:
        return "parakeet_mlx"

    def check_requirements(self) -> List[str]:
        missing: List[str] = []
        # Import-spec checks only: avoid triggering MLX device init in menu availability checks.
        if find_spec("mlx") is None:
            missing.append("Install MLX: pip install mlx")
        if find_spec("parakeet_mlx") is None:
            missing.append("Install Parakeet MLX runtime: pip install parakeet-mlx")

        return missing

    @staticmethod
    def _is_mlx_env_init_failure(error: Exception) -> bool:
        msg = str(error)
        return "NSRangeException" in msg or "libmlx" in msg or "Metal" in msg

    def _ensure_model_loaded(self, model: str) -> None:
        if self._model is not None and self._model_name == model:
            return

        try:
            import parakeet_mlx

            self._module = parakeet_mlx
            # Keep this adapter tolerant to small API differences across versions.
            if hasattr(parakeet_mlx, "from_pretrained"):
                self._model = parakeet_mlx.from_pretrained(model)
            elif hasattr(parakeet_mlx, "ParakeetModel") and hasattr(parakeet_mlx.ParakeetModel, "from_pretrained"):
                self._model = parakeet_mlx.ParakeetModel.from_pretrained(model)
            else:
                # Some builds expose only a top-level transcribe API.
                self._model = None
            self._model_name = model
        except Exception as e:
            raise RuntimeError(f"Failed to load Parakeet MLX model '{model}': {e}")

    def _transcribe(self, audio_path: Path, model: str, language: str) -> str:
        self._ensure_model_loaded(model)
        assert self._module is not None

        # Prefer loaded model object's methods when available.
        if self._model is not None:
            if hasattr(self._model, "transcribe_file"):
                out = self._model.transcribe_file(str(audio_path), language=language)
                return str(out if isinstance(out, str) else out.get("text", "")).strip()
            if hasattr(self._model, "transcribe"):
                out = self._model.transcribe(str(audio_path), language=language)
                return str(out if isinstance(out, str) else out.get("text", "")).strip()

        # Fallback to module-level API.
        if hasattr(self._module, "transcribe"):
            out = self._module.transcribe(str(audio_path), model=model, language=language)
            return str(out if isinstance(out, str) else out.get("text", "")).strip()

        raise RuntimeError("Unsupported mlx_parakeet API: missing transcribe method")

    def transcribe(self, audio_path: str | Path, model: str, language: str, **kwargs) -> EngineResult:
        start = time.time()
        audio_path = Path(audio_path)

        try:
            duration = _audio_duration_seconds(audio_path)
            transcript = self._transcribe(audio_path, model=model, language=language)
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
            error_message = "MLX unusable in current execution environment" if self._is_mlx_env_init_failure(e) else str(e)
            return EngineResult(
                engine=self.engine_name,
                model=model,
                sample_id=audio_path.stem,
                audio_path=str(audio_path),
                transcript="",
                elapsed_seconds=elapsed,
                real_time_factor=None,
                info={"error": error_message, "model": model, "language": language},
            )
