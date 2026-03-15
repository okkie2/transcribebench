"""Adapter for Parakeet models running on Apple Silicon via MLX."""

from __future__ import annotations

import inspect
import time
import wave
from importlib.util import find_spec
from pathlib import Path
import os
from typing import Any, List, Optional

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

        import parakeet_mlx

        self._module = parakeet_mlx
        # Accept either a fully qualified HF repo id or a short model id.
        # For short ids we also try the mlx-community namespace.
        candidates = [model]
        if "/" not in model:
            candidates.append(f"mlx-community/{model}")

        last_error: Exception | None = None
        for candidate in candidates:
            try:
                # Keep this adapter tolerant to small API differences across versions.
                if hasattr(parakeet_mlx, "from_pretrained"):
                    self._model = parakeet_mlx.from_pretrained(candidate)
                elif hasattr(parakeet_mlx, "ParakeetModel") and hasattr(parakeet_mlx.ParakeetModel, "from_pretrained"):
                    self._model = parakeet_mlx.ParakeetModel.from_pretrained(candidate)
                else:
                    # Some builds expose only a top-level transcribe API.
                    self._model = None
                self._model_name = candidate
                return
            except Exception as e:
                last_error = e

        assert last_error is not None
        raise RuntimeError(
            f"Failed to load Parakeet MLX model '{model}' (also tried inferred repo aliases): {last_error}"
        )

    def _extract_text(self, output: object) -> str:
        if isinstance(output, str):
            return output.strip()
        if isinstance(output, list):
            parts = [self._extract_text(item) for item in output]
            return " ".join([p for p in parts if p]).strip()
        if isinstance(output, dict):
            for key in ("text", "transcript", "transcription", "prediction"):
                val = output.get(key)
                if isinstance(val, str) and val.strip():
                    return val.strip()
            # Some outputs nest text in candidate/result structures.
            for key in ("result", "results", "candidates", "hypotheses"):
                if key in output:
                    text = self._extract_text(output[key])
                    if text:
                        return text
        return ""

    def _call_with_supported_kwargs(self, fn: Any, *args: Any, **kwargs: Any) -> Any:
        """Call a Parakeet API while dropping kwargs it does not declare."""
        try:
            signature = inspect.signature(fn)
        except (TypeError, ValueError):
            return fn(*args, **kwargs)

        if any(param.kind == inspect.Parameter.VAR_KEYWORD for param in signature.parameters.values()):
            return fn(*args, **kwargs)

        supported_kwargs = {
            key: value for key, value in kwargs.items() if key in signature.parameters
        }
        return fn(*args, **supported_kwargs)

    def _transcribe(self, audio_path: Path, model: str, language: str) -> str:
        self._ensure_model_loaded(model)
        assert self._module is not None

        # Prefer loaded model object's methods when available.
        if self._model is not None:
            if hasattr(self._model, "transcribe_file"):
                out = self._call_with_supported_kwargs(
                    self._model.transcribe_file,
                    str(audio_path),
                    language=language,
                )
                return self._extract_text(out)
            if hasattr(self._model, "transcribe"):
                out = self._call_with_supported_kwargs(
                    self._model.transcribe,
                    str(audio_path),
                    language=language,
                )
                return self._extract_text(out)

        # Fallback to module-level API.
        if hasattr(self._module, "transcribe"):
            out = self._call_with_supported_kwargs(
                self._module.transcribe,
                str(audio_path),
                model=self._model_name or model,
                language=language,
            )
            return self._extract_text(out)

        raise RuntimeError("Unsupported mlx_parakeet API: missing transcribe method")

    def transcribe(self, audio_path: str | Path, model: str, language: str, **kwargs) -> EngineResult:
        start = time.time()
        audio_path = Path(audio_path)

        try:
            duration = _audio_duration_seconds(audio_path)
            transcript = self._transcribe(audio_path, model=model, language=language)
            if not transcript:
                raise RuntimeError("Parakeet MLX returned empty transcript")
            elapsed = time.time() - start
            rtf = None
            if duration and duration > 0:
                rtf = elapsed / duration
            debug_enabled = os.environ.get("TRANSCRIBEBENCH_DEBUG_PARAKEET", "").lower() in ("1", "true", "yes")
            if debug_enabled:
                print(
                    f"[parakeet_mlx debug] sample={audio_path.name} model={self._model_name or model} "
                    f"duration={duration} elapsed={elapsed:.3f} transcript={transcript[:160]!r}"
                )

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
                info={
                    "error": error_message,
                    "model": self._model_name or model,
                    "language": language,
                    "audio_path": str(audio_path),
                },
            )
