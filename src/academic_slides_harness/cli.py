"""Small CLI entrypoint for smoke checks."""

from __future__ import annotations

import argparse
import json
import re
import shutil
import socket
import sys
from pathlib import Path
from typing import Any

from academic_slides_harness import __version__


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    if args.command == "doctor" and args.doctor_target == "arcade":
        return _doctor_arcade(args)
    if args.command == "doctor" and args.doctor_target == "secrets":
        return _doctor_secrets(args)
    if args.command == "doctor":
        parser.print_help(file=sys.stderr)
        return 2
    print(f"academic-slides-harness {__version__}")
    return 0


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="academic-slides-harness")
    subparsers = parser.add_subparsers(dest="command")

    doctor = subparsers.add_parser("doctor", help="Run local environment checks.")
    doctor_targets = doctor.add_subparsers(dest="doctor_target")
    arcade = doctor_targets.add_parser("arcade", help="Check local Arcade MCP readiness.")
    arcade.add_argument("--json", action="store_true", help="Print machine-readable JSON.")
    arcade.add_argument("--arcade-cli-path", help="Explicit Arcade CLI executable path.")
    arcade.add_argument(
        "--check-http-endpoints",
        action="store_true",
        help="Also check legacy local HTTP engine/worker endpoints.",
    )
    arcade.add_argument("--engine-host", default="127.0.0.1")
    arcade.add_argument("--engine-port", type=int, default=9099)
    arcade.add_argument("--worker-host", default="127.0.0.1")
    arcade.add_argument("--worker-port", type=int, default=8002)
    arcade.add_argument("--timeout", type=float, default=1.0)

    secrets = doctor_targets.add_parser(
        "secrets",
        help="Scan local config files for raw secret patterns without printing values.",
    )
    secrets.add_argument("--json", action="store_true", help="Print machine-readable JSON.")
    secrets.add_argument(
        "--path",
        action="append",
        default=[],
        help="File or directory to scan. Can be passed more than once.",
    )
    return parser


def _doctor_arcade(args: argparse.Namespace) -> int:
    report = diagnose_arcade(
        arcade_cli_path=args.arcade_cli_path,
        engine_host=args.engine_host,
        engine_port=args.engine_port,
        worker_host=args.worker_host,
        worker_port=args.worker_port,
        timeout=args.timeout,
        check_http_endpoints=args.check_http_endpoints,
    )
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        for check in report["checks"]:
            status = "ok" if check["ok"] else "fail"
            print(f"{check['name']}: {status} - {check['message']}")
    return 0 if report["ok"] else 1


def _doctor_secrets(args: argparse.Namespace) -> int:
    report = scan_secret_paths(paths=[Path(path) for path in args.path] or _default_secret_paths())
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        if report["ok"]:
            print("secrets: ok - no raw secret patterns found")
        else:
            for finding in report["findings"]:
                print(
                    f"{finding['kind']}: fail - {finding['path']}:{finding['line']} "
                    f"- {finding['message']}"
                )
    return 0 if report["ok"] else 1


def diagnose_arcade(
    *,
    arcade_cli_path: str | None = None,
    engine_host: str = "127.0.0.1",
    engine_port: int = 9099,
    worker_host: str = "127.0.0.1",
    worker_port: int = 8002,
    timeout: float = 1.0,
    check_http_endpoints: bool = False,
) -> dict[str, Any]:
    checks = [
        _check_arcade_cli(arcade_cli_path),
        _check_local_stdio_entrypoint(_project_root()),
    ]
    if check_http_endpoints:
        checks.extend(
            [
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
        )
    return {"ok": all(check["ok"] for check in checks), "checks": checks}


def scan_secret_paths(*, paths: list[Path]) -> dict[str, Any]:
    findings: list[dict[str, Any]] = []
    scanned_paths: list[str] = []
    for path in paths:
        resolved = path.resolve()
        if not resolved.exists():
            findings.append(
                {
                    "kind": "missing_path",
                    "path": str(resolved),
                    "line": 0,
                    "message": "Configured scan path does not exist.",
                }
            )
            continue
        for file_path in _iter_secret_scan_files(resolved):
            scanned_paths.append(str(file_path))
            findings.extend(_scan_secret_file(file_path))
    return {
        "ok": not findings,
        "scanned_paths": sorted(scanned_paths),
        "findings": sorted(findings, key=lambda finding: (finding["path"], finding["line"])),
    }


def _iter_secret_scan_files(path: Path) -> list[Path]:
    if path.is_file():
        return [path]
    ignored_dirs = {".git", ".pytest_cache", ".ruff_cache", ".venv", "runs"}
    files: list[Path] = []
    for candidate in path.rglob("*"):
        if any(part in ignored_dirs for part in candidate.parts):
            continue
        if candidate.is_file():
            files.append(candidate.resolve())
    return sorted(files)


def _scan_secret_file(path: Path) -> list[dict[str, Any]]:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except UnicodeDecodeError:
        return []

    findings: list[dict[str, Any]] = []
    for line_number, line in enumerate(lines, start=1):
        if _RAW_API_KEY_PATTERN.search(line):
            findings.append(
                {
                    "kind": "raw_api_key",
                    "path": str(path),
                    "line": line_number,
                    "message": "Raw API key pattern found; use an environment variable reference.",
                }
            )
        if _PRIVATE_KEY_BEGIN_PATTERN.search(line):
            findings.append(
                {
                    "kind": "private_key_block",
                    "path": str(path),
                    "line": line_number,
                    "message": "Private key block found; move key material out of config files.",
                }
            )
    return findings


def _check_arcade_cli(arcade_cli_path: str | None) -> dict[str, Any]:
    resolved = _resolve_arcade_cli(arcade_cli_path)
    if resolved is None:
        return {
            "name": "arcade_cli",
            "ok": False,
            "message": "Arcade CLI was not found on PATH or at the configured path.",
            "details": {"configured_path": arcade_cli_path},
        }
    return {
        "name": "arcade_cli",
        "ok": True,
        "message": f"Arcade CLI found at {resolved}",
        "details": {"path": str(resolved)},
    }


def _check_local_stdio_entrypoint(project_root: Path) -> dict[str, Any]:
    server_path = project_root / "server.py"
    if not server_path.exists():
        return {
            "name": "local_stdio_entrypoint",
            "ok": False,
            "message": "server.py was not found in the current project root.",
            "details": {
                "project_root": str(project_root.resolve()),
                "expected_entrypoint": str(server_path.resolve()),
            },
        }
    return {
        "name": "local_stdio_entrypoint",
        "ok": True,
        "message": "Local stdio MCP entrypoint is available.",
        "details": {
            "path": str(server_path.resolve()),
            "entrypoint": str(server_path.resolve()),
            "stdio_command": "uv run python server.py stdio",
            "arcade_command": f"arcade mcp stdio --cwd {project_root.resolve()}",
        },
    }


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


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

    return None


def _default_secret_paths() -> list[Path]:
    repo_root = Path(__file__).resolve().parents[2]
    return [
        repo_root / "AGENTS.md",
        repo_root / "README.md",
        repo_root / "compat",
        repo_root / "docs",
        repo_root / "pyproject.toml",
    ]


_RAW_API_KEY_PATTERN = re.compile(r"\bsk-(?:proj-)?[A-Za-z0-9_-]{20,}\b")
_PRIVATE_KEY_BEGIN_PATTERN = re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")


if __name__ == "__main__":
    raise SystemExit(main())
