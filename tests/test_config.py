"""Unit tests for TranscribeBench configuration."""

import pathlib

from transcribebench.config import Config


def test_load_default_config(tmp_path: pathlib.Path) -> None:
    config_path = tmp_path / "config.yaml"
    config_path.write_text("""language: nl\n""")

    config = Config.load(config_path)
    assert config.language == "nl"
    assert config.dataset.sample_size == 50
    assert config.dataset.url.startswith("http")
    assert len(config.engines) > 0
    assert any(e.engine == "mlx_whisper" and e.enabled for e in config.engines)
