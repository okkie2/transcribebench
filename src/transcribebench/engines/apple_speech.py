"""Adapters for Apple's SpeechAnalyzer-based transcription APIs."""

from __future__ import annotations

import json
import os
import platform
import shutil
import subprocess
import sys
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


class _AppleSpeechBaseEngine(EngineAdapter):
    """Shared adapter that shells out to a tiny Swift helper."""

    _LANGUAGE_TO_LOCALE = {
        "nl": "nl-NL",
    }

    helper_mode = ""

    def check_requirements(self) -> List[str]:
        missing: List[str] = []

        if sys.platform != "darwin":
            missing.append("Apple Speech is only available on macOS.")
            return missing

        version = platform.mac_ver()[0]
        try:
            major = int((version or "0").split(".", 1)[0])
        except ValueError:
            major = 0
        if major < 26:
            missing.append("Apple Speech requires macOS 26 or newer.")

        if shutil.which("swift") is None:
            missing.append("Swift toolchain not available. Install Xcode or Command Line Tools.")

        return missing

    def _repo_root(self) -> Path:
        cwd = Path.cwd()
        if (cwd / "src" / "transcribebench").exists():
            return cwd

        path = Path(__file__).resolve()
        for parent in path.parents:
            if (parent / "src" / "transcribebench").exists():
                return parent

        raise RuntimeError("Could not locate repository root.")

    def _helper_source(self) -> Path:
        return self._repo_root() / "tools" / "apple_speech_cli.swift"

    def _helper_binary(self) -> Path:
        return self._repo_root() / ".cache" / "apple_speech" / "apple-speech-cli"

    def _ensure_helper_built(self) -> Path:
        source = self._helper_source()
        binary = self._helper_binary()

        if not source.exists():
            raise RuntimeError(f"Apple Speech helper source not found: {source}")

        binary.parent.mkdir(parents=True, exist_ok=True)
        module_cache = self._repo_root() / ".cache" / "swift-module-cache"
        module_cache.mkdir(parents=True, exist_ok=True)

        if binary.exists() and binary.stat().st_mtime >= source.stat().st_mtime:
            return binary

        cmd = [
            "swiftc",
            "-parse-as-library",
            "-O",
            "-o",
            str(binary),
            str(source),
        ]
        env = dict(os.environ, SWIFT_MODULECACHE_PATH=str(module_cache))
        proc = subprocess.run(cmd, capture_output=True, text=True, env=env)
        if proc.returncode != 0:
            stderr = (proc.stderr or "").strip()
            raise RuntimeError(f"Failed to build Apple Speech helper: {stderr or 'swiftc failed'}")

        return binary

    def _resolve_locale(self, model: str, language: str) -> str:
        if model and "-" in model:
            return model
        if language in self._LANGUAGE_TO_LOCALE:
            return self._LANGUAGE_TO_LOCALE[language]
        return model or language

    def _run_helper(self, audio_path: Path, locale: str) -> dict:
        helper = self._ensure_helper_built()
        cmd = [str(helper)]
        if self.helper_mode:
            cmd.append(self.helper_mode)
        cmd.extend(["--audio", str(audio_path), "--locale", locale])
        proc = subprocess.run(cmd, capture_output=True, text=True)
        if proc.returncode != 0:
            stderr = (proc.stderr or "").strip()
            raise RuntimeError(
                f"Apple Speech helper failed (code {proc.returncode}): {stderr or 'no stderr output'}"
            )

        try:
            return json.loads(proc.stdout.strip() or "{}")
        except json.JSONDecodeError as e:
            raise RuntimeError(f"Apple Speech helper returned invalid JSON: {e}") from e

    def transcribe(self, audio_path: str | Path, model: str, language: str, **kwargs) -> EngineResult:
        start = time.time()
        audio_path = Path(audio_path)

        try:
            locale = self._resolve_locale(model, language)
            duration = _audio_duration_seconds(audio_path)
            payload = self._run_helper(audio_path, locale)
            transcript = str(payload.get("text", "")).strip()
            if not transcript:
                raise RuntimeError(str(payload.get("error", "Apple Speech returned empty transcript")))

            elapsed = time.time() - start
            rtf = elapsed / duration if duration and duration > 0 else None
            return EngineResult(
                engine=self.engine_name,
                model=model,
                sample_id=audio_path.stem,
                audio_path=str(audio_path),
                transcript=transcript,
                elapsed_seconds=elapsed,
                real_time_factor=rtf,
                info={
                    "model": model,
                    "language": language,
                    "locale": locale,
                },
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
                info={
                    "error": str(e),
                    "model": model,
                    "language": language,
                    "audio_path": str(audio_path),
                },
            )


class AppleSpeechEngine(_AppleSpeechBaseEngine):
    """SpeechTranscriber-backed engine."""

    @property
    def engine_name(self) -> str:
        return "apple_speech"


class AppleDictationEngine(_AppleSpeechBaseEngine):
    """DictationTranscriber-backed engine."""

    helper_mode = "--dictation"

    @property
    def engine_name(self) -> str:
        return "apple_dictation"
