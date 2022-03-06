"""Tests for TCP k8s probe functionality."""

import pytest
import socket
import threading
import time

from py_tcp_probe import ProbeStatusProvider


@pytest.fixture(scope="session")
def tcp_probe():
    """TCP server used in tests."""
    ip, port = 'localhost', 8887
    server = ProbeStatusProvider(ip, port)
    client_socks = []

    def mk_client():
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client_socks.append(sock)
        sock.connect((ip, port))
        send = lambda message: sock.sendall(bytes(message, 'ascii'))
        receive = lambda: str(sock.recv(1024), 'ascii')
        return send, receive
    try:
        server.start()

        yield server, mk_client

        for sock in client_socks:
            sock.close()
    finally:
        server.shutdown()

def test_liveness_default(tcp_probe):
    _, client_factory = tcp_probe
    send, receive = client_factory()
    send("live?")
    assert receive() == 'False'


def test_readiness_default(tcp_probe):
    _, client_factory = tcp_probe
    send, receive = client_factory()
    send("ready?")
    assert receive() == 'False'


def test_liveness_can_change(tcp_probe):
    server, client_factory = tcp_probe
    send, receive = client_factory()
    server.set_liveness(True)
    send("live?")
    assert receive() == 'True'


def test_readiness_can_change(tcp_probe):
    server, client_factory = tcp_probe
    send, receive = client_factory()
    server.set_readiness(True)
    send("ready?")
    assert receive() == 'True'


@pytest.mark.parametrize("is_alive", [True, False])
@pytest.mark.parametrize("is_ready", [True, False])
def test_readiness_and_liveness_can_change(tcp_probe, is_alive: bool, is_ready: bool):
    server, client_factory = tcp_probe
    server.set_readiness(is_ready)
    server.set_liveness(is_alive)

    send, receive = client_factory()
    send("ready?")
    assert receive() == str(is_ready)

    send, receive = client_factory()
    send("live?")
    assert receive() == str(is_alive)
