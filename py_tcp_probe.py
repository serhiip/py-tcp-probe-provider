"""TCP kubernetes probe."""

import socket
import threading
import socketserver

class ThreadedProbeHandler(socketserver.BaseRequestHandler):

    def handle(self):
        """Handle incoming messages."""
        data = str(self.request.recv(1024), 'ascii')
        status = self.server.liveness_probe_reader()

        if data == "ready?":
            status = self.server.readiness_probe_reader()
        elif data == "live?":
            status = self.server.liveness_probe_reader()

        self.request.sendall(bytes(str(status), 'ascii'))

class ThreadedTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):

    def __init__(self, liveness_probe_reader, readiness_probe_reader, server_address, RequestHandlerClass):
        self.liveness_probe_reader = liveness_probe_reader
        self.readiness_probe_reader = readiness_probe_reader
        super().__init__(server_address, RequestHandlerClass)

    def server_bind(self):
        """Override to set socket options to reuse old sockets via https://stackoverflow.com/a/18858817"""
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.bind(self.server_address)

class ProbeStatusProvider:

    def __init__(self, host: str, port: int = 8888):
        """Create new probe provider."""
        self.__liveness_probe = threading.Event()
        self.__readiness_probe = threading.Event()
        self.__server = ThreadedTCPServer(self.__liveness_probe.is_set, self.__readiness_probe.is_set, (host, port), ThreadedProbeHandler)
        self.__server_thread = threading.Thread(target=self.__server.serve_forever)
        self.__server_thread.daemon = True

    def start(self):
        self.__server_thread.start()

    def shutdown(self):
        self.__server.shutdown()

    def set_liveness(self, status: bool):
        self.__set_probe_status(self.__liveness_probe, status)

    def set_readiness(self, status: bool):
        self.__set_probe_status(self.__readiness_probe, status)

    def __set_probe_status(self, probe: threading.Event, status: bool):
        probe.set() if status  else probe.clear()
