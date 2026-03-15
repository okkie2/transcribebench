from __future__ import annotations

import sys
import wave
from pathlib import Path

from transcribebench.engines.parakeet_mlx import ParakeetMlxEngine


def _write_test_wav(path: Path, sample_rate: int = 16_000, duration_s: float = 0.1) -> None:
    frames = int(sample_rate * duration_s)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sample_rate)
        w.writeframes(b"\x00\x00" * frames)


class _FakeModel:
    def transcribe_file(self, audio_path: str, language: str = "nl") -> dict:
        return {"text": "dit is een test"}


def test_parakeet_mlx_model_fallback_and_resolution(monkeypatch) -> None:
    attempts: list[str] = []

    class _FakeModule:
        @staticmethod
        def from_pretrained(model_id: str):
            attempts.append(model_id)
            if model_id == "parakeet-ctc-1.1b":
                raise FileNotFoundError("config.json missing")
            if model_id == "mlx-community/parakeet-ctc-1.1b":
                return _FakeModel()
            raise AssertionError(f"unexpected model id {model_id}")

    engine = ParakeetMlxEngine()
    monkeypatch.setattr("transcribebench.engines.parakeet_mlx.find_spec", lambda name: object())
    monkeypatch.setitem(sys.modules, "parakeet_mlx", _FakeModule)

    engine._ensure_model_loaded("parakeet-ctc-1.1b")

    assert attempts == ["parakeet-ctc-1.1b", "mlx-community/parakeet-ctc-1.1b"]
    assert engine._model_name == "mlx-community/parakeet-ctc-1.1b"


def test_parakeet_mlx_empty_transcript_returns_error(tmp_path: Path, monkeypatch) -> None:
    wav_path = tmp_path / "sample.wav"
    _write_test_wav(wav_path)

    class _FakeModule:
        @staticmethod
        def from_pretrained(model_id: str):
            class _Model:
                def transcribe_file(self, audio_path: str, language: str = "nl") -> dict:
                    return {"text": "   "}

            return _Model()

    engine = ParakeetMlxEngine()
    monkeypatch.setitem(sys.modules, "parakeet_mlx", _FakeModule)

    result = engine.transcribe(wav_path, model="parakeet-ctc-1.1b", language="nl")

    assert result.transcript == ""
    assert "error" in result.info
    assert "empty transcript" in str(result.info["error"]).lower()


def test_parakeet_mlx_ignores_unsupported_language_kwarg(tmp_path: Path, monkeypatch) -> None:
    wav_path = tmp_path / "sample.wav"
    _write_test_wav(wav_path)

    class _FakeModule:
        @staticmethod
        def from_pretrained(model_id: str):
            class _Model:
                def transcribe(self, audio_path: str) -> dict:
                    return {"text": "dit werkt nu"}

            return _Model()

    engine = ParakeetMlxEngine()
    monkeypatch.setitem(sys.modules, "parakeet_mlx", _FakeModule)

    result = engine.transcribe(wav_path, model="parakeet-ctc-1.1b", language="nl")

    assert result.transcript == "dit werkt nu"
    assert "error" not in result.info


def test_parakeet_mlx_extracts_text_from_nested_output() -> None:
    engine = ParakeetMlxEngine()
    text = engine._extract_text(
        {
            "results": [
                {"timestamp": [0.0, 1.0], "text": "dit"},
                {"timestamp": [1.0, 2.0], "text": "werkt"},
            ]
        }
    )
    assert text == "dit werkt"


def test_parakeet_mlx_extracts_text_from_object_output() -> None:
    class _AlignedResultLike:
        def __init__(self, text: str) -> None:
            self.text = text

    engine = ParakeetMlxEngine()
    text = engine._extract_text(_AlignedResultLike("dit komt uit aligned result"))
    assert text == "dit komt uit aligned result"
