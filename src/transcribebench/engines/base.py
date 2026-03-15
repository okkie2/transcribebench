"""Engine adapter base classes."""

from __future__ import annotations

import dataclasses
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, Optional


@dataclasses.dataclass(frozen=True)
class EngineResult:
    engine: str
    model: str
    sample_id: str
    audio_path: str

    # The engine's raw transcript output
    transcript: str

    # Timings
    elapsed_seconds: float
    real_time_factor: Optional[float] = None

    # Optional detailed info, e.g. stderr output, model used, etc.
    info: Dict[str, Any] = dataclasses.field(default_factory=dict)


class EngineAdapter(ABC):
    """Base adapter interface for an engine."""

    @property
    @abstractmethod
    def engine_name(self) -> str:
        ...

    @property
    def name(self) -> str:
        # Backwards-compatible alias for older call sites.
        return self.engine_name

    @abstractmethod
    def check_requirements(self) -> list[str]:
        """Return a list of human-friendly messages describing missing requirements.

        If the list is empty, the engine is considered installable.
        """

    @abstractmethod
    def transcribe(
        self,
        audio_path: str | Path,
        model: str,
        language: str,
        **kwargs: Any,
    ) -> EngineResult:
        """Transcribe a single audio file.

        This method should not raise for expected errors; instead, callers can
        treat exceptions as a failure case.
        """
