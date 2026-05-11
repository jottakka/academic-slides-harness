import json
import socket
from pathlib import Path

from academic_slides_harness.cli import diagnose_arcade, main


def test_doctor_without_target_prints_help_and_fails(capsys) -> None:
    exit_code = main(["doctor"])

    captured = capsys.readouterr()
    assert exit_code == 2
    assert "Run local environment checks" in captured.err


def test_doctor_arcade_defaults_to_local_stdio_without_http_endpoint_checks(
    capsys,
    tmp_path,
) -> None:
    exit_code = main(
        [
            "doctor",
            "arcade",
            "--json",
            "--arcade-cli-path",
            str(tmp_path / "missing-arcade.exe"),
        ]
    )

    output = json.loads(capsys.readouterr().out)
    check_names = {check["name"] for check in output["checks"]}

    assert exit_code == 1
    assert output["ok"] is False
    assert check_names == {"arcade_cli", "local_stdio_entrypoint"}


def test_doctor_arcade_does_not_probe_home_tool_bin_by_default(
    capsys,
    monkeypatch,
    tmp_path: Path,
) -> None:
    arcade = tmp_path / "tool-bin" / "arcade.exe"
    arcade.parent.mkdir(parents=True)
    arcade.write_text("fake arcade", encoding="utf-8")
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    monkeypatch.setattr("academic_slides_harness.cli.shutil.which", lambda _command: None)

    exit_code = main(["doctor", "arcade", "--json"])

    output = json.loads(capsys.readouterr().out)
    arcade_check = {check["name"]: check for check in output["checks"]}["arcade_cli"]
    assert exit_code == 1
    assert arcade_check["ok"] is False
    assert "expected_path" not in arcade_check["details"]


def test_diagnose_arcade_finds_stdio_entrypoint_outside_repo_cwd(
    monkeypatch,
    tmp_path: Path,
) -> None:
    monkeypatch.chdir(tmp_path)

    output = diagnose_arcade(arcade_cli_path=str(tmp_path / "missing-arcade.exe"))

    checks_by_name = {check["name"]: check for check in output["checks"]}
    assert checks_by_name["local_stdio_entrypoint"]["ok"] is True
    assert Path(checks_by_name["local_stdio_entrypoint"]["details"]["path"]).name == "server.py"


def test_doctor_arcade_checks_http_endpoints_only_when_requested(
    capsys,
    tmp_path,
) -> None:
    engine_port = _unused_tcp_port()
    worker_port = _unused_tcp_port()

    exit_code = main(
        [
            "doctor",
            "arcade",
            "--json",
            "--arcade-cli-path",
            str(tmp_path / "missing-arcade.exe"),
            "--check-http-endpoints",
            "--engine-port",
            str(engine_port),
            "--worker-port",
            str(worker_port),
            "--timeout",
            "0.01",
        ]
    )

    output = json.loads(capsys.readouterr().out)
    check_names = {check["name"] for check in output["checks"]}

    assert exit_code == 1
    assert output["ok"] is False
    assert check_names == {
        "arcade_cli",
        "arcade_engine",
        "arcade_worker",
        "local_stdio_entrypoint",
    }
    checks_by_name = {check["name"]: check for check in output["checks"]}
    assert checks_by_name["arcade_engine"]["ok"] is False
    assert checks_by_name["arcade_worker"]["ok"] is False


def test_doctor_secrets_reports_findings_without_leaking_secret_values(
    capsys,
    tmp_path,
) -> None:
    config_path = tmp_path / "engine.yaml"
    fake_key = "sk-proj-" + ("x" * 48)
    config_path.write_text(
        "\n".join(
            [
                "llm:",
                f"  api_key: {fake_key}",
                "security:",
                "  private_key: |",
                "    -----BEGIN PRIVATE KEY-----",
                "    fake-test-key-material",
                "    -----END PRIVATE KEY-----",
            ]
        ),
        encoding="utf-8",
    )

    exit_code = main(["doctor", "secrets", "--json", "--path", str(config_path)])

    raw_output = capsys.readouterr().out
    output = json.loads(raw_output)

    assert exit_code == 1
    assert output["ok"] is False
    assert {finding["kind"] for finding in output["findings"]} == {
        "private_key_block",
        "raw_api_key",
    }
    assert all(finding["path"] == str(config_path.resolve()) for finding in output["findings"])
    assert fake_key not in raw_output
    assert "fake-test-key-material" not in raw_output


def test_doctor_models_reports_redacted_provider_configuration(
    capsys,
    monkeypatch,
) -> None:
    fake_key = "sk-proj-" + ("x" * 48)
    monkeypatch.setenv("OPENAI_API_KEY", fake_key)
    monkeypatch.setenv("OPENAI_BASE_URL", "http://127.0.0.1:9999/v1")
    monkeypatch.setattr(
        "academic_slides_harness.llm.providers.OllamaProvider.is_available",
        lambda _self: False,
    )
    monkeypatch.setattr(
        "academic_slides_harness.llm.providers.OllamaProvider.list_models",
        lambda _self: [],
    )

    exit_code = main(["doctor", "models", "--json"])

    raw_output = capsys.readouterr().out
    output = json.loads(raw_output)
    assert exit_code == 0
    assert output["ok"] is True
    assert output["providers"]["openai"]["api_key_configured"] is True
    assert output["providers"]["openai"]["base_url_configured"] is True
    assert fake_key not in raw_output


def _unused_tcp_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.bind(("127.0.0.1", 0))
        return int(probe.getsockname()[1])
