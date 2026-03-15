"""Adapter for NVIDIA Parakeet CTC models via NVIDIA NeMo."""

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


class ParakeetCtcEngine(EngineAdapter):
    """Engine adapter for NeMo ASR CTC models such as nvidia/parakeet-ctc-1.1b."""

    def __init__(self) -> None:
        self._model = None
        self._model_name: Optional[str] = None

    @property
    def engine_name(self) -> str:
        return "nemo_ctc"

    def check_requirements(self) -> List[str]:
        missing: List[str] = []
        try:
            import nemo.collections.asr  # noqa: F401
        except ImportError:
            missing.append("Install NVIDIA NeMo ASR: pip install nemo_toolkit[asr]")

        try:
            import torch  # noqa: F401
        except ImportError:
            missing.append("Install PyTorch: pip install torch")

        return missing

    def _ensure_model_loaded(self, model: str) -> None:
        if self._model is not None and self._model_name == model:
            return

        try:
            from nemo.collections.asr.models import ASRModel

            # NeMo loads from NGC/HF model identifiers through from_pretrained.
            self._model = ASRModel.from_pretrained(model_name=model)
            self._model_name = model
        except Exception as e:
            raise RuntimeError(f"Failed to load NeMo model '{model}': {e}")

    def transcribe(self, audio_path: str | Path, model: str, language: str, **kwargs) -> EngineResult:
        start = time.time()
        audio_path = Path(audio_path)

        try:
            self._ensure_model_loaded(model)
            assert self._model is not None

            duration = _audio_duration_seconds(audio_path)
            # NeMo returns list[str] for batch input.
            out = self._model.transcribe(paths2audio_files=[str(audio_path)])
            transcript = ""
            if isinstance(out, list) and out:
                transcript = str(out[0]).strip()
            else:
                transcript = str(out).strip()

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
