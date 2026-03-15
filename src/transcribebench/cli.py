"""Command-line interface for TranscribeBench."""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path
from typing import Any

import yaml
from .config import Config
from .engines import FasterWhisperEngine, MlxWhisperEngine, ParakeetCtcEngine, WhisperCppEngine
from .runner import BenchmarkRunner


def _adapter_mapping():
    return {
        "mlx_whisper": MlxWhisperEngine(),
        "faster_whisper": FasterWhisperEngine("faster_whisper"),
        "faster_whisper_large": FasterWhisperEngine("faster_whisper_large"),
        "whisper_cpp": WhisperCppEngine(),
        "nemo_ctc": ParakeetCtcEngine(),
    }


def _build_targets(config: Config) -> list[BenchmarkRunner.RunTarget]:
    adapters = _adapter_mapping()
    targets: list[BenchmarkRunner.RunTarget] = []
    for spec in config.enabled_engines():
        adapter = adapters.get(spec.engine)
        if adapter is None:
            continue
        targets.append(BenchmarkRunner.RunTarget(adapter=adapter, model=spec.model))
    return targets


def _load_raw_config(path: str) -> dict[str, Any]:
    p = Path(path)
    if not p.exists():
        return {}
    with p.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _save_raw_config(path: str, raw: dict[str, Any]) -> None:
    p = Path(path)
    with p.open("w", encoding="utf-8") as f:
        yaml.safe_dump(raw, f, sort_keys=False, allow_unicode=True)


def _set_sample_size(config_path: str, sample_size: int) -> None:
    raw = _load_raw_config(config_path)
    raw.setdefault("dataset", {})
    raw["dataset"]["sample_size"] = sample_size
    _save_raw_config(config_path, raw)


def _set_engines(config_path: str, engines: list[dict[str, Any]]) -> None:
    raw = _load_raw_config(config_path)
    raw["engines"] = engines
    _save_raw_config(config_path, raw)


def _check_setup_state() -> tuple[bool, list[str]]:
    notes: list[str] = []
    repo_root = Path.cwd()
    whisper_cpp_dir = repo_root / "third_party" / "whisper.cpp"
    whisper_cpp_bin = whisper_cpp_dir / "build" / "bin" / "whisper-cli"

    ready = True
    if not whisper_cpp_dir.exists():
        ready = False
        notes.append("whisper.cpp submodule is missing")
    if not whisper_cpp_bin.exists():
        ready = False
        notes.append("whisper.cpp binary is not built")
    return ready, notes


def _check_dataset_state(config: Config) -> tuple[str, str]:
    samples_dir = Path(config.output.dataset_cache) / config.language
    metadata_path = samples_dir / "metadata.json"
    if not metadata_path.exists():
        return "missing", "dataset metadata not found"

    try:
        with metadata_path.open("r", encoding="utf-8") as f:
            raw = json.load(f)
    except Exception:
        return "stale", "dataset metadata is unreadable"

    meta = raw.get("_meta", {}) if isinstance(raw, dict) else {}
    if meta.get("sample_size") != config.dataset.sample_size or meta.get("seed") != config.dataset.seed:
        return "stale", "sample size or seed differs from current config"

    samples = raw.get("samples", []) if isinstance(raw, dict) else []
    if not samples:
        return "stale", "no samples in cache"

    for s in samples:
        p = Path(s.get("audio_path", ""))
        if not p.exists() or p.stat().st_size == 0:
            return "stale", "cached audio files are missing or empty"
    return "ready", "cache matches current config"


def _estimate_runtime(config: Config) -> str:
    results_path = Path(config.output.results_dir) / "results.json"
    if not results_path.exists():
        return "Estimate unavailable yet (no previous local benchmark runs found)."

    try:
        with results_path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        rows = data.get("results", [])
    except Exception:
        return "Estimate unavailable yet (could not read previous results)."

    enabled = [(e.engine, e.model) for e in config.enabled_engines()]
    if not enabled:
        return "Estimate unavailable (no engines enabled)."

    per_combo_avg: dict[tuple[str, str], float] = {}
    for engine, model in enabled:
        combo_rows = [
            r
            for r in rows
            if r.get("engine") == engine and r.get("model") == model and isinstance(r.get("elapsed_seconds"), (int, float))
        ]
        if combo_rows:
            per_combo_avg[(engine, model)] = sum(float(r["elapsed_seconds"]) for r in combo_rows) / len(combo_rows)

    if not per_combo_avg:
        return "Estimate unavailable yet (no matching historical engine/model timings)."

    lines = ["Estimated benchmark time (rough):"]
    total_seconds = 0.0
    for engine, model in enabled:
        avg = per_combo_avg.get((engine, model))
        label = f"{engine} ({model})"
        if avg is None:
            lines.append(f"- {label}: n/a (no history)")
            continue
        estimate = avg * config.dataset.sample_size
        total_seconds += estimate
        lo = max(0.0, estimate * 0.8)
        hi = estimate * 1.2
        lines.append(f"- {label}: ~{int(lo // 60)} to {int(hi // 60)} min")

    if total_seconds > 0:
        total_lo = total_seconds * 0.8
        total_hi = total_seconds * 1.2
        lines.append(f"- Total: ~{int(total_lo // 60)} to {int(total_hi // 60)} min")
    return "\n".join(lines)


def _run_setup() -> None:
    print("Preparing whisper.cpp dependencies...")
    subprocess.run(["git", "submodule", "update", "--init", "--recursive"], check=True)
    subprocess.run(["make"], cwd=str(Path("third_party") / "whisper.cpp"), check=True)


def _run_fetch(config_path: str) -> None:
    print("Refreshing dataset cache...")
    _cmd_fetch_dataset(argparse.Namespace(config=config_path))


def _run_benchmark_with_auto_prepare(config_path: str) -> int:
    config = Config.load(config_path)
    print("Checking setup...")
    setup_ready, setup_notes = _check_setup_state()
    if not setup_ready:
        for note in setup_notes:
            print(f"- {note}")
        _run_setup()
        print("Setup complete.")
    else:
        print("Setup is ready.")

    print("Checking dataset cache...")
    dataset_state, dataset_note = _check_dataset_state(config)
    print(f"- Dataset status: {dataset_state} ({dataset_note})")
    if dataset_state != "ready":
        _run_fetch(config_path)
        print("Dataset cache refreshed.")

    print("Running benchmark...")
    return _cmd_run_benchmark(argparse.Namespace(config=config_path))


def _show_status(config_path: str) -> None:
    config = Config.load(config_path)
    setup_ready, _ = _check_setup_state()
    dataset_state, dataset_note = _check_dataset_state(config)
    enabled = [f"{e.engine} ({e.model})" for e in config.enabled_engines()]

    print("\nCurrent status")
    print(f"- Setup: {'ready' if setup_ready else 'missing'}")
    print(f"- Dataset: {dataset_state} ({dataset_note})")
    print(f"- Sample size: {config.dataset.sample_size}")
    print(f"- Language: {config.language}")
    print(f"- Enabled engine/model pairs: {', '.join(enabled) if enabled else 'none'}")
    print("- Output files:")
    print(f"  - {Path(config.output.results_dir) / 'results.json'}")
    print(f"  - {Path(config.output.reports_dir) / 'report.md'}")
    print(f"  - {Path(config.output.reports_dir) / 'results.csv'}")
    print(_estimate_runtime(config))


def _interactive_set_sample_size(config_path: str) -> None:
    config = Config.load(config_path)
    print(f"Current sample size: {config.dataset.sample_size}")
    print("Guidance: small (5-20) = quick smoke test, medium (30-100) = useful comparison, large (150+) = slower but more reliable.")
    while True:
        raw = input("Enter new sample size (or press Enter to cancel): ").strip()
        if not raw:
            print("Cancelled.")
            return
        if not raw.isdigit() or int(raw) <= 0:
            print("Please enter a positive integer.")
            continue
        new_size = int(raw)
        _set_sample_size(config_path, new_size)
        print(f"Sample size updated to {new_size}. Dataset will refresh on next benchmark run.")
        print(_estimate_runtime(Config.load(config_path)))
        return


def _interactive_select_engines(config_path: str) -> None:
    hints = {
        "mlx_whisper": "Apple Silicon optimized (MLX)",
        "faster_whisper": "Fast CTranslate2 backend",
        "faster_whisper_large": "Large-model faster-whisper",
        "whisper_cpp": "Portable whisper.cpp backend",
        "nemo_ctc": "NVIDIA NeMo CTC runtime",
    }

    while True:
        config = Config.load(config_path)
        engines = list(config.engines)
        print("\nSelect engine/model pairs (toggle by number, Enter to finish):")
        for idx, spec in enumerate(engines, start=1):
            mark = "x" if spec.enabled else " "
            print(f"{idx}. [{mark}] {spec.engine} ({spec.model}) - {hints.get(spec.engine, '')}".strip())

        choice = input("Choice: ").strip()
        if not choice:
            enabled = [f"{e.engine} ({e.model})" for e in engines if e.enabled]
            print(f"Saved. Enabled: {', '.join(enabled) if enabled else 'none'}")
            print(_estimate_runtime(Config.load(config_path)))
            return
        if not choice.isdigit() or not (1 <= int(choice) <= len(engines)):
            print("Invalid selection.")
            continue

        selected_idx = int(choice) - 1
        updated: list[dict[str, Any]] = []
        for i, spec in enumerate(engines):
            updated.append(
                {
                    "engine": spec.engine,
                    "model": spec.model,
                    "enabled": (not spec.enabled) if i == selected_idx else spec.enabled,
                }
            )
        _set_engines(config_path, updated)


def _open_most_recent_report(config_path: str) -> None:
    config = Config.load(config_path)
    cwd = Path.cwd()

    candidates = list(cwd.glob("reports*/report.md"))
    default_report = Path(config.output.reports_dir) / "report.md"
    if default_report.exists() and default_report not in candidates:
        candidates.append(default_report)

    if not candidates:
        print("No report found yet. Run a benchmark first.")
        return

    latest = max(candidates, key=lambda p: p.stat().st_mtime)
    print(f"Most recent report: {latest}")
    print("\n--- report.md ---\n")
    print(latest.read_text(encoding="utf-8"))


def _cmd_menu(args: argparse.Namespace) -> int:
    config_path = args.config
    while True:
        print("\nTranscribeBench Menu")
        print("1. Run benchmark")
        print("2. Set sample size")
        print("3. Select engines")
        print("4. Show current status / configuration")
        print("5. Open most recent report")
        print("6. Exit")
        choice = input("Choose an action [1-6]: ").strip()

        if choice == "1":
            try:
                _run_benchmark_with_auto_prepare(config_path)
            except subprocess.CalledProcessError as e:
                print(f"Command failed with exit code {e.returncode}.")
        elif choice == "2":
            _interactive_set_sample_size(config_path)
        elif choice == "3":
            _interactive_select_engines(config_path)
        elif choice == "4":
            _show_status(config_path)
        elif choice == "5":
            _open_most_recent_report(config_path)
        elif choice == "6":
            print("Goodbye.")
            return 0
        else:
            print("Please choose 1, 2, 3, 4, 5, or 6.")


def _cmd_setup(args: argparse.Namespace) -> int:
    config = Config.load(args.config)
    targets = _build_targets(config)

    messages = []
    seen: set[str] = set()
    for target in targets:
        if target.adapter.engine_name in seen:
            continue
        seen.add(target.adapter.engine_name)
        missing = target.adapter.check_requirements()
        if missing:
            messages.append(f"Engine {target.adapter.engine_name} requirements:")
            messages.extend([f"  - {m}" for m in missing])

    if messages:
        print("Setup checks completed with messages:")
        print("\n".join(messages))
        return 1

    print("All known requirements appear satisfied.")
    return 0


def _cmd_fetch_dataset(args: argparse.Namespace) -> int:
    config = Config.load(args.config)
    runner = BenchmarkRunner(config, [])
    runner.dataset_provider.fetch(
        language=config.language,
        size=config.dataset.sample_size,
        seed=config.dataset.seed,
        url=config.dataset.url,
    )
    print("Dataset fetched (or already cached).")
    return 0


def _cmd_run_benchmark(args: argparse.Namespace) -> int:
    config = Config.load(args.config)
    targets = _build_targets(config)

    usable_targets: list[BenchmarkRunner.RunTarget] = []
    for target in targets:
        missing = target.adapter.check_requirements()
        if missing:
            print(f"Skipping {target.adapter.engine_name} ({target.model}): missing requirements:")
            for m in missing:
                print(f"  - {m}")
        else:
            usable_targets.append(target)

    if not usable_targets:
        print("No usable engines available; please install dependencies or enable a supported engine.")
        return 1

    runner = BenchmarkRunner(config, usable_targets)
    results = runner.run()
    runner.save_results(results)
    print(f"Benchmark complete. Results written to: {config.output.results_dir}")
    return 0


def _cmd_report(args: argparse.Namespace) -> int:
    config = Config.load(args.config)

    out_dir = Path(config.output.reports_dir)
    if not out_dir.exists():
        print(f"Report directory does not exist: {out_dir}")
        return 1

    print(f"Report artifacts are in: {out_dir}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="transcribebench")
    parser.add_argument("--config", default="config.yaml", help="Path to config file")

    subparsers = parser.add_subparsers(dest="command", required=False)

    subparsers.add_parser("setup", help="Check prerequisites for enabled engines")
    subparsers.add_parser("fetch-dataset", help="Download/cache dataset subset")
    subparsers.add_parser("run-benchmark", help="Run the benchmark and store results")
    subparsers.add_parser("report", help="Generate human-readable report artifacts")
    subparsers.add_parser("menu", help="Open interactive CLI menu")

    args = parser.parse_args(argv)

    if args.command is None or args.command == "menu":
        return _cmd_menu(args)
    if args.command == "setup":
        return _cmd_setup(args)
    if args.command == "fetch-dataset":
        return _cmd_fetch_dataset(args)
    if args.command == "run-benchmark":
        return _cmd_run_benchmark(args)
    if args.command == "report":
        return _cmd_report(args)

    parser.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
