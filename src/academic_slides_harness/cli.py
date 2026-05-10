"""Small CLI entrypoint for smoke checks."""

from __future__ import annotations

import argparse
import json
import shutil
import socket
from pathlib import Path
from typing import Any

from academic_slides_harness import __version__


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    if args.command == "doctor" and args.doctor_target == "arcade":
        return _doctor_arcade(args)
    print(f"academic-slides-harness {__version__}")
    return 0


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="academic-slides-harness")
    subparsers = parser.add_subparsers(dest="command")

    doctor = subparsers.add_parser("doctor", help="Run local environment checks.")
    doctor_targets = doctor.add_subparsers(dest="doctor_target")
    arcade = doctor_targets.add_parser("arcade", help="Check Arcade CLI, engine, and worker.")
    arcade.add_argument("--json", action="store_true", help="Print machine-readable JSON.")
    arcade.add_argument("--arcade-cli-path", help="Explicit Arcade CLI executable path.")
    arcade.add_argument("--engine-host", default="127.0.0.1")
    arcade.add_argument("--engine-port", type=int, default=9099)
    arcade.add_argument("--worker-host", default="127.0.0.1")
    arcade.add_argument("--worker-port", type=int, default=8002)
    arcade.add_argument("--timeout", type=float, default=1.0)
    return parser


def _doctor_arcade(args: argparse.Namespace) -> int:
    report = diagnose_arcade(
        arcade_cli_path=args.arcade_cli_path,
        engine_host=args.engine_host,
        engine_port=args.engine_port,
        worker_host=args.worker_host,
        worker_port=args.worker_port,
        timeout=args.timeout,
    )
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        for check in report["checks"]:
            status = "ok" if check["ok"] else "fail"
            print(f"{check['name']}: {status} - {check['message']}")
    return 0 if report["ok"] else 1


def diagnose_arcade(
    *,
    arcade_cli_path: str | None = None,
    engine_host: str = "127.0.0.1",
    engine_port: int = 9099,
    worker_host: str = "127.0.0.1",
    worker_port: int = 8002,
    timeout: float = 1.0,
) -> dict[str, Any]:
    checks = [
        _check_arcade_cli(arcade_cli_path),
        _check_tcp_endpoint(
            name="arcade_engine",
            host=engine_host,
            port=engine_port,
            timeout=timeout,
        ),
        _check_tcp_endpoint(
            name="arcade_worker",
            host=worker_host,
            port=worker_port,
            timeout=timeout,
        ),
    ]
    return {"ok": all(check["ok"] for check in checks), "checks": checks}


def _check_arcade_cli(arcade_cli_path: str | None) -> dict[str, Any]:
    resolved = _resolve_arcade_cli(arcade_cli_path)
    if resolved is None:
        return {
            "name": "arcade_cli",
            "ok": False,
            "message": "Arcade CLI was not found on PATH or at the expected Windows install path.",
            "details": {
                "expected_path": str(_default_windows_arcade_path()),
                "configured_path": arcade_cli_path,
            },
        }
    return {
        "name": "arcade_cli",
        "ok": True,
        "message": f"Arcade CLI found at {resolved}",
        "details": {"path": str(resolved)},
    }


def _check_tcp_endpoint(*, name: str, host: str, port: int, timeout: float) -> dict[str, Any]:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            pass
    except OSError as exc:
        return {
            "name": name,
            "ok": False,
            "message": f"{host}:{port} is not accepting TCP connections.",
            "details": {"host": host, "port": port, "error": str(exc)},
        }
    return {
        "name": name,
        "ok": True,
        "message": f"{host}:{port} is accepting TCP connections.",
        "details": {"host": host, "port": port},
    }


def _resolve_arcade_cli(arcade_cli_path: str | None) -> Path | None:
    if arcade_cli_path:
        path = Path(arcade_cli_path).expanduser()
        return path.resolve() if path.exists() else None

    for command in ["arcade", "arcade.exe"]:
        found = shutil.which(command)
        if found is not None:
            return Path(found).resolve()

    fallback = _default_windows_arcade_path()
    return fallback.resolve() if fallback.exists() else None


def _default_windows_arcade_path() -> Path:
    return Path.home() / ".local" / "bin" / "arcade.exe"


if __name__ == "__main__":
    raise SystemExit(main())
