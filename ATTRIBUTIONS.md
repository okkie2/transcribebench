# Attributions

TranscribeBench benchmarks and integrates several third-party speech models,
runtimes, and tools. This file provides high-level attribution for the main
components used by the project.

## Core upstream components

| Component | Role in TranscribeBench | Owner / Maintainer | Upstream |
| --- | --- | --- | --- |
| Whisper model family | Speech-to-text models used by multiple benchmark engines | OpenAI | https://openai.com/index/whisper/ |
| `faster-whisper` | Optimized Whisper inference runtime | SYSTRAN | https://github.com/SYSTRAN/faster-whisper |
| `whisper.cpp` | C/C++ Whisper runtime used by the `whisper_cpp` engine | Georgi Gerganov and contributors | https://github.com/ggerganov/whisper.cpp |
| Parakeet model family | Speech-to-text models used by the `parakeet_mlx` engine | NVIDIA | https://huggingface.co/nvidia/parakeet-tdt-0.6b-v3 |
| `parakeet-mlx` | MLX integration for Parakeet models | `parakeet-mlx` maintainers | https://github.com/thewh1teagle/parakeet-mlx |
| Apple Speech framework | Native on-device transcription for `apple_speech` and `apple_dictation` | Apple | https://developer.apple.com/documentation/speech |
| MLX | Apple Silicon ML runtime used by MLX-backed engines | Apple | https://github.com/ml-explore/mlx |
| `mlx-community` model conversions | MLX-formatted model distributions used in benchmark configs | MLX Community contributors | https://huggingface.co/mlx-community |
| Mozilla Common Voice | Example benchmark dataset source | Mozilla | https://commonvoice.mozilla.org/ |

## Notes

- TranscribeBench is licensed separately under the terms in [LICENSE.md](/Users/joostokkinga/Code/TranscribeBench/LICENSE.md).
- Third-party components remain subject to their own licenses and terms.
- This file is informational and does not replace upstream license texts.
