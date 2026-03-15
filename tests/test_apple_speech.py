from __future__ import annotations

import json
import platform
import subprocess
import sys
from pathlib import Path

from transcribebench.cli import _adapter_mapping
from transcribebench.engines.apple_speech import AppleDictationEngine, AppleSpeechEngine


def test_apple_speech_registered() -> None:
    adapters = _adapter_mapping()
    assert "apple_speech" in adapters
    assert isinstance(adapters["apple_speech"], AppleSpeechEngine)
    assert "apple_dictation" in adapters
    assert isinstance(adapters["apple_dictation"], AppleDictationEngine)


def test_apple_speech_unavailable_off_macos(monkeypatch) -> None:
    engine = AppleSpeechEngine()
    monkeypatch.setattr(sys, "platform", "linux")

    missing = engine.check_requirements()

    assert any("macos" in item.lower() for item in missing)


def test_apple_speech_unavailable_before_macos_26(monkeypatch) -> None:
    engine = AppleSpeechEngine()
    monkeypatch.setattr(sys, "platform", "darwin")
    monkeypatch.setattr(platform, "mac_ver", lambda: ("15.6", ("", "", ""), "arm64"))

    missing = engine.check_requirements()

    assert any("macos 26" in item.lower() for item in missing)


def test_apple_speech_transcribe_returns_helper_error(tmp_path: Path, monkeypatch) -> None:
    audio_path = tmp_path / "sample.mp3"
    audio_path.write_bytes(b"fake")

    engine = AppleSpeechEngine()
    monkeypatch.setattr(engine, "_ensure_helper_built", lambda: Path("/tmp/apple-speech-cli"))
    monkeypatch.setattr(engine, "_resolve_locale", lambda model, language: "nl-NL")

    def fake_run(*args, **kwargs):
        return subprocess.CompletedProcess(
            args[0],
            0,
            stdout=json.dumps({"error": "Speech assets for locale nl-NL are not installed on this machine."}),
            stderr="",
        )

    monkeypatch.setattr(subprocess, "run", fake_run)

    result = engine.transcribe(audio_path, model="nl-NL", language="nl")

    assert result.transcript == ""
    assert "error" in result.info
    assert "not installed" in result.info["error"].lower()


def test_apple_dictation_uses_dictation_helper_mode(tmp_path: Path, monkeypatch) -> None:
    audio_path = tmp_path / "sample.mp3"
    audio_path.write_bytes(b"fake")

    engine = AppleDictationEngine()
    monkeypatch.setattr(engine, "_ensure_helper_built", lambda: Path("/tmp/apple-speech-cli"))
    monkeypatch.setattr(engine, "_resolve_locale", lambda model, language: "nl-NL")

    def fake_run(*args, **kwargs):
        assert "--dictation" in args[0]
        return subprocess.CompletedProcess(
            args[0],
            0,
            stdout=json.dumps({"text": "dit werkt"}),
            stderr="",
        )

    monkeypatch.setattr(subprocess, "run", fake_run)

    result = engine.transcribe(audio_path, model="nl-NL", language="nl")

    assert result.transcript == "dit werkt"
