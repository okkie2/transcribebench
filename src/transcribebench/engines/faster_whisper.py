"""Adapter for faster-whisper."""

from __future__ import annotations

import time
import wave
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


class FasterWhisperEngine(EngineAdapter):
    def __init__(self, name: str = "faster_whisper") -> None:
        self._model = None
        self._model_name: Optional[str] = None
        self._engine_name = name

    @property
    def name(self) -> str:
        return self._engine_name

    def check_requirements(self) -> List[str]:
        missing: List[str] = []
        try:
            import faster_whisper  # noqa: F401
        except ImportError:
            missing.append("Install faster-whisper: pip install faster-whisper")

        try:
            import torch  # noqa: F401
        except ImportError:
            missing.append(
                "Install torch (PyTorch) for faster-whisper: pip install torch"
            )

        return missing

    def _ensure_model_loaded(self, model: str) -> None:
        if self._model is not None and self._model_name == model:
            return

        try:
            from faster_whisper import WhisperModel

            self._model = WhisperModel(model, device="auto")
            self._model_name = model
        except Exception as e:
            raise RuntimeError(f"Failed to load faster-whisper model '{model}': {e}")

    def transcribe(
        self,
        audio_path: str | Path,
        model: str,
        language: str,
        **kwargs,
    ) -> EngineResult:
        start = time.time()
        audio_path = Path(audio_path)

        try:
            self._ensure_model_loaded(model)
            assert self._model is not None

            duration = _audio_duration_seconds(audio_path)
            segments, _info = self._model.transcribe(
                str(audio_path),
                language=language,
                task="transcribe",
            )

            # segments is a generator of segment objects with a `.text` attribute.
            transcript = "".join([s.text for s in segments])
            elapsed = time.time() - start
            rtf = None
            if duration and duration > 0:
                rtf = elapsed / duration

            return EngineResult(
                engine=self.name,
                sample_id=audio_path.stem,
                audio_path=str(audio_path),
                transcript=transcript.strip(),
                elapsed_seconds=elapsed,
                real_time_factor=rtf,
                info={"model": model, "language": language},
            )
        except Exception as e:
            elapsed = time.time() - start
            return EngineResult(
                engine=self.name,
                sample_id=audio_path.stem,
                audio_path=str(audio_path),
                transcript="",
                elapsed_seconds=elapsed,
                real_time_factor=None,
                info={"error": str(e), "model": model, "language": language},
            )
