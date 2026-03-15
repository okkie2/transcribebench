"""Engine adapters for TranscribeBench."""

from .base import EngineAdapter, EngineResult
from .apple_speech import AppleDictationEngine, AppleSpeechEngine
from .mlx_whisper import MlxWhisperEngine
from .faster_whisper import FasterWhisperEngine
from .whisper_cpp import WhisperCppEngine
from .parakeet_mlx import ParakeetMlxEngine

__all__ = [
    "EngineAdapter",
    "EngineResult",
    "AppleDictationEngine",
    "AppleSpeechEngine",
    "MlxWhisperEngine",
    "FasterWhisperEngine",
    "WhisperCppEngine",
    "ParakeetMlxEngine",
]
