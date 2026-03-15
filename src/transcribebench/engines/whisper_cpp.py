"""Adapter for whisper.cpp via the whispercpp Python binding."""

from __future__ import annotations

import time
from pathlib import Path
from typing import List, Optional

from .base import EngineAdapter, EngineResult


class WhisperCppEngine(EngineAdapter):
    def __init__(self) -> None:
        self._model = None
        self._model_name: Optional[str] = None
        self._shim_loaded = False
        self._binding_failed = False

    @property
    def name(self) -> str:
        return "whisper_cpp"

    def check_requirements(self) -> List[str]:
        missing: List[str] = []

        # Prefer the python binding path; if that does not work, we fall back to
        # using the whisper.cpp CLI binary (built from source).
        try:
            self._ensure_whispercpp_imported()
        except Exception as e:
            missing.append(
                "whispercpp import failed: {}. "
                "This repository can fall back to the whisper.cpp CLI if built from source.".format(
                    e
                )
            )

        # Ensure we can run the whisper.cpp CLI (fallback).
        if self._find_whispercpp_binary() is None:
            missing.append(
                "whisper.cpp CLI not available. Run `make` in third_party/whisper.cpp to build it."
            )

        return missing

    def _ensure_whispercpp_imported(self):
        """Import whispercpp, applying a macOS shim if needed.

        whispercpp wheels on macOS may be built against a Python ABI that expects
        the symbol __PyThreadState_UncheckedGet to be present. Some Python
        versions (e.g. 3.14) do not export this symbol, causing an import error.
        This method attempts to work around that by preloading a tiny shim
        library that exposes the missing symbol and then re-importing.
        """

        if self._shim_loaded:
            import whispercpp  # noqa: F401
            return whispercpp

        try:
            import whispercpp  # noqa: F401
            return whispercpp
        except Exception as e:
            if "__PyThreadState_UncheckedGet" not in str(e):
                raise

        # Build/load shim and retry import
        try:
            self._load_whispercpp_shim()
            import whispercpp  # noqa: F401
            return whispercpp
        except Exception as e:
            raise RuntimeError(
                "Failed to import whispercpp (even after applying shim): %s" % e
            )

    def _load_whispercpp_shim(self):
        """Build and preload a small dynamic library exporting __PyThreadState_UncheckedGet."""

        if self._shim_loaded:
            return

        import ctypes
        import subprocess
        import sysconfig
        import tempfile
        from pathlib import Path

        shim_dir = Path(tempfile.gettempdir()) / "transcribebench_whispercpp_shim"
        shim_dir.mkdir(parents=True, exist_ok=True)

        source_path = shim_dir / "whispercpp_shim.c"
        lib_path = shim_dir / "whispercpp_shim.dylib"

        # Generate source, but only overwrite if it doesn't exist to avoid rebuilding constantly.
        if not source_path.exists():
            source_path.write_text(
                """#include <Python.h>\n\nPyThreadState* __PyThreadState_UncheckedGet(void) {\n    return PyThreadState_Get();\n}\n"""
            )

        # Build the shim if it doesn't exist.
        if not lib_path.exists():
            include_dir = sysconfig.get_paths()["include"]
            cmd = [
                "clang",
                "-shared",
                "-o",
                str(lib_path),
                str(source_path),
                "-I",
                include_dir,
                "-undefined",
                "dynamic_lookup",
            ]
            subprocess.run(cmd, check=True)

        # Preload the shim so the symbol is available when the whispercpp extension is loaded.
        ctypes.CDLL(str(lib_path), mode=ctypes.RTLD_GLOBAL)
        self._shim_loaded = True

    def _ensure_model_loaded(self, model: str):
        if self._model is not None and self._model_name == model:
            return

        whispercpp = self._ensure_whispercpp_imported()

        try:
            self._model = whispercpp.Whisper.from_pretrained(model)
            self._model_name = model
        except Exception as e:
            raise RuntimeError(f"Failed to load whisper.cpp model '{model}': {e}")

    def _repo_root(self) -> Path:
        """Locate the repository root containing the `third_party/whisper.cpp` source."""

        # Prefer the current working directory if it contains the expected tree.
        cwd = Path.cwd()
        if (cwd / "third_party" / "whisper.cpp").exists():
            return cwd

        # Fall back to searching upwards from this source file.
        path = Path(__file__).resolve()
        for parent in path.parents:
            if (parent / "third_party" / "whisper.cpp").exists():
                return parent

        raise RuntimeError(
            "Could not locate repository root containing third_party/whisper.cpp"
        )

    def _find_whispercpp_binary(self) -> Optional[Path]:
        """Locate the whisper.cpp CLI binary if it exists."""

        repo_root = self._repo_root()
        bin_path = repo_root / "third_party" / "whisper.cpp" / "build" / "bin" / "whisper-cli"
        return bin_path if bin_path.exists() else None

    def _build_whispercpp_binary(self) -> Path:
        """Build the whisper.cpp CLI binary using `make`."""

        repo_root = self._repo_root()
        whisper_cpp_dir = repo_root / "third_party" / "whisper.cpp"

        import subprocess

        subprocess.run(["make"], cwd=str(whisper_cpp_dir), check=True)

        bin_path = whisper_cpp_dir / "build" / "bin" / "whisper-cli"
        if not bin_path.exists():
            raise RuntimeError(f"whisper-cli binary not found after build: {bin_path}")

        return bin_path

    def _ensure_whispercpp_binary(self) -> Path:
        """Return the whisper.cpp CLI binary, building it if needed."""

        bin_path = self._find_whispercpp_binary()
        if bin_path is not None:
            return bin_path

        return self._build_whispercpp_binary()

    def _ensure_model_file(self, model: str) -> Path:
        """Ensure that a ggml model file exists for the given model spec."""

        # If the model argument is already a path to a file, just use it.
        path = Path(model)
        if path.is_file():
            return path

        # Map popular preconverted models to their corresponding ggml filenames.
        # See: https://github.com/ggerganov/whisper.cpp/tree/master/models
        known = {
            "tiny": "ggml-tiny.bin",
            "base": "ggml-base.bin",
            "small": "ggml-small.bin",
            "medium": "ggml-medium.bin",
            "large": "ggml-large.bin",
            "large-v1": "ggml-large-v1.bin",
        }

        if model not in known:
            raise RuntimeError(
                f"Unknown whisper.cpp model '{model}'. Provide a local .bin path or one of: {', '.join(sorted(known))}"
            )

        model_file = self._repo_root() / "dataset_cache" / "whisper_cpp_models" / known[model]
        model_file.parent.mkdir(parents=True, exist_ok=True)

        if model_file.exists():
            return model_file

        # Download the model from the official repository.
        url = f"https://huggingface.co/ggerganov/whisper.cpp/resolve/main/{known[model]}"

        try:
            from urllib.request import urlretrieve

            urlretrieve(url, str(model_file))
        except Exception as e:
            raise RuntimeError(f"Failed to download whisper.cpp model '{model}' from {url}: {e}")

        return model_file

    def _transcribe_with_cli(self, audio_path: Path, model: str, language: str) -> str:
        """Transcribe a single file by invoking the whisper.cpp CLI binary."""

        bin_path = self._ensure_whispercpp_binary()
        model_file = self._ensure_model_file(model)

        import subprocess

        cmd = [
            str(bin_path),
            "--no-prints",
            "-nt",
            "-m",
            str(model_file),
            "-l",
            language,
            str(audio_path),
        ]

        # whisper-cli prints transcript to stdout; capture it.
        proc = subprocess.run(cmd, capture_output=True, text=True)
        if proc.returncode != 0:
            raise RuntimeError(
                f"whisper.cpp CLI failed (code {proc.returncode}): {proc.stderr.strip()}"
            )

        return proc.stdout.strip()

    def transcribe(self, audio_path: str | Path, model: str, language: str, **kwargs) -> EngineResult:
        start = time.time()
        audio_path = Path(audio_path)

        # Prefer the python binding for speed, but fall back to the CLI if it fails.
        transcript: str
        if not self._binding_failed:
            try:
                self._ensure_model_loaded(model)
                assert self._model is not None
                transcript = self._model.transcribe_from_file(str(audio_path))
            except Exception:
                self._binding_failed = True
                transcript = self._transcribe_with_cli(audio_path, model, language)
        else:
            transcript = self._transcribe_with_cli(audio_path, model, language)

        elapsed = time.time() - start

        return EngineResult(
            engine=self.name,
            sample_id=audio_path.stem,
            audio_path=str(audio_path),
            transcript=str(transcript).strip(),
            elapsed_seconds=elapsed,
            real_time_factor=None,
            info={"model": model, "language": language},
        )
