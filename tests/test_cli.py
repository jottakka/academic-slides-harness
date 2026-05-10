import json
import socket

from academic_slides_harness.cli import main


def test_doctor_arcade_reports_cli_engine_and_worker_failures(
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
    assert check_names == {"arcade_cli", "arcade_engine", "arcade_worker"}
    assert all(check["ok"] is False for check in output["checks"])


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
