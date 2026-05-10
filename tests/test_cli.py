import json
import socket

from academic_slides_harness.cli import main


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


def _unused_tcp_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.bind(("127.0.0.1", 0))
        return int(probe.getsockname()[1])
