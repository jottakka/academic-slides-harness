import socket

import pytest


@pytest.mark.arcade_live
def test_arcade_engine_and_worker_ports_are_available() -> None:
    unavailable = [
        f"{host}:{port}"
        for host, port in [("127.0.0.1", 9099), ("127.0.0.1", 8002)]
        if not _can_connect(host, port)
    ]
    if unavailable:
        pytest.skip(f"Arcade live endpoints unavailable: {', '.join(unavailable)}")


def _can_connect(host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.settimeout(1.0)
        return probe.connect_ex((host, port)) == 0
