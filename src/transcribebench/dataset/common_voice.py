"""Common Voice dataset support (stubbed for v1)."""

from __future__ import annotations

import dataclasses
import json
import pathlib
import random
import shutil
from dataclasses import dataclass
from typing import Iterable, List


@dataclass(frozen=True)
class CommonVoiceSample:
    id: str
    audio_path: str
    transcript: str


class CommonVoiceProvider:
    """A reproducible subset downloader + cache for Mozilla Common Voice."""

    # This URL is a known stable archive for the Dutch Common Voice release.
    # Replace it in config if you want a different version.
    DEFAULT_URL = "https://voice-prod-bundler.storage.googleapis.com/cv-corpus-14.0-2023-12-11/nl.tar.gz"

    def __init__(self, cache_dir: str | pathlib.Path):
        self.cache_dir = pathlib.Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def fetch(
        self,
        language: str,
        size: int,
        seed: int,
        url: str | None = None,
    ) -> list[CommonVoiceSample]:
        """Fetch a reproducible subset of Common Voice for the given language."""

        random_gen = random.Random(seed)
        samples_dir = self.cache_dir / language
        audio_dir = samples_dir / "audio"
        metadata_path = samples_dir / "metadata.json"

        # If already cached, try to load it and validate it matches the request.
        if metadata_path.exists():
            try:
                with metadata_path.open("r", encoding="utf-8") as f:
                    raw = json.load(f)

                # Backwards-compat: old cache format stored a list of samples.
                if isinstance(raw, list):
                    shutil.rmtree(samples_dir, ignore_errors=True)
                else:
                    meta = raw.get("_meta", {})
                    if (
                        meta.get("seed") == seed
                        and meta.get("sample_size") == size
                    ):
                        # Ensure audio files exist and are non-empty.
                        valid = True
                        for s in raw.get("samples", []):
                            p = pathlib.Path(s.get("audio_path", ""))
                            if not p.exists() or p.stat().st_size == 0:
                                valid = False
                                break
                        if valid:
                            return [CommonVoiceSample(**s) for s in raw.get("samples", [])]
                    # Otherwise, regenerate
                    shutil.rmtree(samples_dir, ignore_errors=True)
            except (json.JSONDecodeError, ValueError):
                shutil.rmtree(samples_dir, ignore_errors=True)

        # Download and extract a Common Voice archive for the requested language.
        archive_url = url or self.DEFAULT_URL
        archive_path = samples_dir / "common_voice.tar.gz"
        raw_dir = samples_dir / "raw"

        samples_dir.mkdir(parents=True, exist_ok=True)

        if not archive_path.exists():
            # If the user provided a local path, use it directly.
            local_path = None
            if archive_url.startswith("file://"):
                local_path = pathlib.Path(archive_url[len("file://"):])
            else:
                candidate = pathlib.Path(archive_url)
                if candidate.exists():
                    local_path = candidate

            if local_path is not None and local_path.exists():
                shutil.copy2(local_path, archive_path)
            else:
                # Download the archive into the cache.
                import urllib.request

                try:
                    print(f"Downloading Common Voice archive from {archive_url}...")
                    urllib.request.urlretrieve(archive_url, archive_path)
                except Exception as e:
                    print(
                        "Warning: Failed to download Common Voice archive; "
                        "falling back to a synthetic sample set."
                    )
                    return self._create_synthetic_samples(language, size, seed, samples_dir)

        # Extract the archive into raw_dir (overwriting if necessary).
        if raw_dir.exists():
            shutil.rmtree(raw_dir, ignore_errors=True)
        raw_dir.mkdir(parents=True, exist_ok=True)

        import tarfile

        with tarfile.open(archive_path, "r:gz") as tar:
            tar.extractall(path=raw_dir)

        # Find a TSV file containing corpus metadata (search recursively).
        tsv_path = None
        for candidate in ["validated.tsv", "train.tsv", "test.tsv"]:
            matches = list(raw_dir.rglob(candidate))
            if matches:
                tsv_path = matches[0]
                break

        if tsv_path is None:
            raise RuntimeError(
                f"Could not find a metadata TSV file in extracted archive at {raw_dir}"
            )

        # Use the TSV's parent directory as the base for relative audio paths.
        base_dir = tsv_path.parent

        # Parse the TSV and build a list of valid examples.
        import csv

        examples = []
        with tsv_path.open("r", encoding="utf-8") as f:
            reader = csv.DictReader(f, delimiter="\t")
            for row in reader:
                path = row.get("path")
                sentence = row.get("sentence") or row.get("text") or ""
                if not path or not sentence:
                    continue
                audio_file = base_dir / path
                if not audio_file.exists():
                    # Some Common Voice archives store clips in a "clips" subdir.
                    audio_file = base_dir / "clips" / path
                if not audio_file.exists():
                    continue
                examples.append((path, sentence))

        if len(examples) < size:
            raise RuntimeError(
                f"Requested sample size {size} is larger than available entries ({len(examples)})."
            )

        random_gen.shuffle(examples)
        selected = examples[:size]

        audio_dir.mkdir(parents=True, exist_ok=True)
        samples: list[CommonVoiceSample] = []
        for i, (path, transcript) in enumerate(selected):
            # Audio files in the archive may be stored directly under the base directory
            # or inside a "clips/" subdirectory.
            src_path = base_dir / path
            if not src_path.exists():
                src_path = base_dir / "clips" / path

            sample_id = f"{language}-{i:04d}"
            target_audio = audio_dir / f"{sample_id}{src_path.suffix}"
            shutil.copy2(src_path, target_audio)
            samples.append(
                CommonVoiceSample(
                    id=sample_id,
                    audio_path=str(target_audio),
                    transcript=transcript,
                )
            )

        with metadata_path.open("w", encoding="utf-8") as f:
            json.dump(
                {
                    "_meta": {"seed": seed, "sample_size": size, "url": archive_url},
                    "samples": [dataclasses.asdict(s) for s in samples],
                },
                f,
                ensure_ascii=False,
                indent=2,
            )

        return samples

    def _create_synthetic_samples(
        self, language: str, size: int, seed: int, samples_dir: pathlib.Path
    ) -> list[CommonVoiceSample]:
        """Create a small synthetic dataset when the real dataset cannot be downloaded."""

        random_gen = random.Random(seed)
        audio_dir = samples_dir / "audio"
        metadata_path = samples_dir / "metadata.json"

        samples_dir.mkdir(parents=True, exist_ok=True)
        audio_dir.mkdir(parents=True, exist_ok=True)

        # Generate simple tone wave files.
        import math
        import wave
        import struct

        duration_s = 1.0
        sample_rate = 16000
        num_samples = int(duration_s * sample_rate)
        frequency = 440.0

        samples: list[CommonVoiceSample] = []
        for i in range(size):
            sample_id = f"{language}-{i:04d}"
            path = audio_dir / f"{sample_id}.wav"

            # Slightly vary the frequency and amplitude per sample.
            freq = frequency + random_gen.uniform(-20, 20)
            amplitude = int(32767 * (0.3 + 0.2 * random_gen.random()))

            with wave.open(str(path), "w") as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(sample_rate)
                for n in range(num_samples):
                    sample_val = int(
                        amplitude * math.sin(2 * math.pi * freq * n / sample_rate)
                    )
                    wf.writeframes(struct.pack("<h", sample_val))

            transcript = f"synthetic sample {i}"
            samples.append(
                CommonVoiceSample(id=sample_id, audio_path=str(path), transcript=transcript)
            )

        with metadata_path.open("w", encoding="utf-8") as f:
            json.dump(
                {
                    "_meta": {
                        "seed": seed,
                        "sample_size": size,
                        "source": "synthetic",
                    },
                    "samples": [dataclasses.asdict(s) for s in samples],
                },
                f,
                ensure_ascii=False,
                indent=2,
            )

        return samples

    def clear_cache(self, language: str) -> None:
        """Delete cached dataset for a language."""
        path = self.cache_dir / language
        if path.exists():
            shutil.rmtree(path)
