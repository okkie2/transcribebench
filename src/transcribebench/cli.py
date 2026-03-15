"""Command-line interface for TranscribeBench."""

from __future__ import annotations

import argparse
import dataclasses
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import yaml
from .config import Config
from .engines import FasterWhisperEngine, MlxWhisperEngine, ParakeetMlxEngine, WhisperCppEngine
from .runner import BenchmarkRunner


def _adapter_mapping():
    return {
        "mlx_whisper": MlxWhisperEngine(),
        "faster_whisper": FasterWhisperEngine("faster_whisper"),
        "faster_whisper_large": FasterWhisperEngine("faster_whisper_large"),
        "whisper_cpp": WhisperCppEngine(),
        "parakeet_mlx": ParakeetMlxEngine(),
    }


def _check_requirements_safe(engine: str) -> list[str]:
    """Run requirement checks in a subprocess so native import crashes are isolated."""
    script = (
        "import json,sys\n"
        "from transcribebench.cli import _adapter_mapping\n"
        "engine=sys.argv[1]\n"
        "adapter=_adapter_mapping().get(engine)\n"
        "if adapter is None:\n"
        "    print(json.dumps({'missing':[f'Unknown engine: {engine}']}))\n"
        "    raise SystemExit(0)\n"
        "try:\n"
        "    missing=adapter.check_requirements()\n"
        "    print(json.dumps({'missing': missing}))\n"
        "except Exception as e:\n"
        "    print(json.dumps({'missing':[str(e)]}))\n"
    )
    proc = subprocess.run(
        [sys.executable, "-c", script, engine],
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        stderr = (proc.stderr or "").strip()
        if "NSRangeException" in stderr and "libmlx" in stderr:
            return ["MLX unusable in this environment (Metal device initialization crash: NSRangeException)"]
        if stderr:
            first_line = stderr.splitlines()[0]
            return [f"requirement check crashed (exit code {proc.returncode}): {first_line}"]
        return [f"requirement check crashed (exit code {proc.returncode})"]
    try:
        payload = json.loads(proc.stdout.strip() or "{}")
    except json.JSONDecodeError:
        return ["requirement check returned unreadable output"]
    missing = payload.get("missing", [])
    return [str(x) for x in missing] if isinstance(missing, list) else ["unknown requirement check failure"]


def _detect_engine_availability() -> tuple[dict[str, Any], dict[str, list[str]]]:
    adapters = _adapter_mapping()
    available: dict[str, Any] = {}
    unavailable: dict[str, list[str]] = {}
    for engine, adapter in adapters.items():
        missing = _check_requirements_safe(engine)
        if missing:
            unavailable[engine] = missing
        else:
            available[engine] = adapter
    return available, unavailable


def _disable_unavailable_engines(config_path: str, unavailable: dict[str, list[str]]) -> bool:
    config = Config.load(config_path)
    changed = False
    updated: list[dict[str, Any]] = []
    for spec in config.engines:
        enabled = spec.enabled
        if spec.engine in unavailable and enabled:
            enabled = False
            changed = True
        updated.append({"engine": spec.engine, "model": spec.model, "enabled": enabled})
    if changed:
        try:
            _set_engines(config_path, updated)
        except OSError:
            # Keep CLI usable if config path is read-only in this environment.
            return False
    return changed


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
        return "missing", "Dataset cache missing: metadata file not found"

    try:
        with metadata_path.open("r", encoding="utf-8") as f:
            raw = json.load(f)
    except Exception:
        return "mismatch", "Dataset cache does not match current configuration. Reason: metadata file is unreadable"

    meta = raw.get("_meta", {}) if isinstance(raw, dict) else {}
    reasons: list[str] = []
    cached_sample_size = meta.get("sample_size")
    cached_seed = meta.get("seed")
    cached_url = meta.get("url")

    if cached_sample_size != config.dataset.sample_size:
        reasons.append(f"sample size changed from {cached_sample_size} to {config.dataset.sample_size}")
    if cached_seed != config.dataset.seed:
        reasons.append(f"seed changed from {cached_seed} to {config.dataset.seed}")
    # URL often encodes dataset version; report it as dataset source/version mismatch.
    if cached_url is not None and cached_url != config.dataset.url:
        reasons.append("dataset source/version URL changed")

    if reasons:
        return "mismatch", "Dataset cache does not match current configuration. Reason: " + "; ".join(reasons)

    samples = raw.get("samples", []) if isinstance(raw, dict) else []
    if not samples:
        return "mismatch", "Dataset cache does not match current configuration. Reason: no samples in cache"

    for s in samples:
        p = Path(s.get("audio_path", ""))
        if not p.exists() or p.stat().st_size == 0:
            return "mismatch", "Dataset cache does not match current configuration. Reason: cached audio files are missing or empty"
    return "ready", "cache matches current config"


def _estimate_runtime(config: Config, allowed_engines: set[str] | None = None) -> str:
    results_path = Path(config.output.results_dir) / "results.json"
    if not results_path.exists():
        return "Estimate unavailable yet (no previous local benchmark runs found)."

    try:
        with results_path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        rows = data.get("results", [])
    except Exception:
        return "Estimate unavailable yet (could not read previous results)."

    enabled_specs = config.enabled_engines()
    if allowed_engines is not None:
        enabled_specs = [e for e in enabled_specs if e.engine in allowed_engines]
    enabled = [(e.engine, e.model) for e in enabled_specs]
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
    print("Checking environment preparation...")
    setup_ready, setup_notes = _check_setup_state()
    if not setup_ready:
        for note in setup_notes:
            print(f"- {note}")
        _run_setup()
        print("Environment preparation complete.")
    else:
        print("Environment is ready.")

    print("Checking dataset cache...")
    dataset_state, dataset_note = _check_dataset_state(config)
    print(f"- Dataset status: {dataset_state} ({dataset_note})")
    if dataset_state != "ready":
        _run_fetch(config_path)
        print("Dataset cache refreshed.")

    print("Running benchmark...")
    return _cmd_run_benchmark(argparse.Namespace(config=config_path))


def _show_status(config_path: str) -> None:
    available, unavailable = _detect_engine_availability()
    _disable_unavailable_engines(config_path, unavailable)
    config = Config.load(config_path)
    setup_ready, _ = _check_setup_state()
    dataset_state, dataset_note = _check_dataset_state(config)
    enabled = [f"{e.engine} ({e.model})" for e in config.enabled_engines() if e.engine in available]

    print("\nCurrent status")
    print(f"- Configuration file: {config_path}")
    print(f"- Environment: {'ready' if setup_ready else 'missing requirements'}")
    print(f"- Dataset: {dataset_state} ({dataset_note})")
    print(f"- Sample size: {config.dataset.sample_size}")
    print(f"- Language: {config.language}")
    print(f"- Enabled engine/model pairs: {', '.join(enabled) if enabled else 'none'}")
    print("- Available engines:")
    for name in sorted(available.keys()):
        print(f"  {name}")
    print("- Unavailable engines:")
    if unavailable:
        for name, missing in sorted(unavailable.items()):
            print(f"  {name} - missing {', '.join(missing)}")
    else:
        print("  none")
    print("- Output files:")
    print(f"  - {Path(config.output.results_dir) / 'results.json'}")
    print(f"  - {Path(config.output.reports_dir) / 'report.md'}")
    print(f"  - {Path(config.output.reports_dir) / 'results.csv'}")
    print(_estimate_runtime(config, allowed_engines=set(available.keys())))


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
        "parakeet_mlx": "Parakeet on MLX (Apple Silicon)",
    }

    while True:
        available, unavailable = _detect_engine_availability()
        _disable_unavailable_engines(config_path, unavailable)
        config = Config.load(config_path)
        engine_to_specs: dict[str, list[EngineSpec]] = {}
        for spec in config.engines:
            engine_to_specs.setdefault(spec.engine, []).append(spec)

        selectable = [engine for engine in engine_to_specs.keys() if engine in available]
        print("\nSelectable engines:")
        for idx, engine in enumerate(selectable, start=1):
            selected = any(s.enabled for s in engine_to_specs[engine])
            mark = "x" if selected else " "
            print(f"{idx}. [{mark}] {engine} - {hints.get(engine, '')}".strip())

        print("\nUnavailable engines on this system:")
        if unavailable:
            for name, missing in sorted(unavailable.items()):
                print(f"- {name} - missing requirements: {', '.join(missing)}")
        else:
            print("- none")

        choice = input("Choice: ").strip()
        if not choice:
            enabled = [f"{e.engine} ({e.model})" for e in config.engines if e.enabled and e.engine in available]
            print(f"Saved. Enabled: {', '.join(enabled) if enabled else 'none'}")
            print(_estimate_runtime(Config.load(config_path), allowed_engines=set(available.keys())))
            return
        if not selectable:
            print("No runnable engines are currently available.")
            continue
        if not choice.isdigit() or not (1 <= int(choice) <= len(selectable)):
            print("Invalid selection.")
            continue

        selected_engine = selectable[int(choice) - 1]
        current = any(s.enabled for s in engine_to_specs[selected_engine])
        updated: list[dict[str, Any]] = []
        for spec in config.engines:
            updated.append(
                {
                    "engine": spec.engine,
                    "model": spec.model,
                    "enabled": (not current) if spec.engine == selected_engine else spec.enabled,
                }
            )
        _set_engines(config_path, updated)


def _open_most_recent_report(config_path: str) -> None:
    config = Config.load(config_path)
    report_path = Path(config.output.reports_dir) / "report.md"
    if not report_path.exists():
        print("No benchmark report found yet. Run a benchmark first.")
        return

    print(f"Most recent report: {report_path}")
    print("\n--- report.md ---\n")
    print(report_path.read_text(encoding="utf-8"))


def _cmd_menu(args: argparse.Namespace) -> int:
    config_path = args.config
    while True:
        print("\nTranscribeBench Menu")
        print("1. Run benchmark")
        print("2. Set sample size")
        print("3. Select engines")
        print("4. Show status")
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
    available, unavailable = _detect_engine_availability()
    _disable_unavailable_engines(args.config, unavailable)
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
        print("Environment preparation checks completed with messages:")
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
    print("Dataset cache refreshed (or already up to date).")
    return 0


def _cmd_run_benchmark(args: argparse.Namespace) -> int:
    available, unavailable = _detect_engine_availability()
    _disable_unavailable_engines(args.config, unavailable)
    config = Config.load(args.config)
    targets = [t for t in _build_targets(config) if t.adapter.engine_name in available]
    if not targets:
        print("No usable engines available; please install dependencies or enable a supported engine.")
        return 1

    runner = BenchmarkRunner(config, targets)
    results = runner.run()
    results.setdefault("run", {})
    results["run"]["config_path"] = str(Path(args.config))
    results["run"]["engines_evaluated"] = [
        {"engine": t.adapter.engine_name, "model": t.model} for t in targets
    ]
    results["run"]["sample_size"] = config.dataset.sample_size
    results["run"]["language"] = config.language
    results["run"]["dataset"] = {
        "provider": config.dataset.provider,
        "url": config.dataset.url,
    }
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
    parser.add_argument("--config", default="config/default.yaml", help="Path to config file")

    subparsers = parser.add_subparsers(dest="command", required=False)

    subparsers.add_parser("prepare-environment", help="Check environment requirements for enabled engines")
    subparsers.add_parser("refresh-dataset", help="Refresh dataset cache for the current configuration")
    subparsers.add_parser("run-benchmark", help="Run the benchmark and store results")
    subparsers.add_parser("report", help="Generate human-readable report artifacts")
    subparsers.add_parser("menu", help="Open interactive CLI menu")

    args = parser.parse_args(argv)

    if args.command is None or args.command == "menu":
        return _cmd_menu(args)
    if args.command == "prepare-environment":
        return _cmd_setup(args)
    if args.command == "refresh-dataset":
        return _cmd_fetch_dataset(args)
    if args.command == "run-benchmark":
        return _cmd_run_benchmark(args)
    if args.command == "report":
        return _cmd_report(args)

    parser.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
