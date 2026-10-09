"""Real loopback checks: live ownership and normal TCP shutdown differ."""
import socket
import unittest

from local_dev import probe_port


class PortProbeTests(unittest.TestCase):
    def listener(self):
        server = socket.socket()
        self.addCleanup(server.close)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind(("127.0.0.1", 0))
        server.listen(1)
        return server

    def test_live_listener_is_rejected(self):
        server = self.listener()
        with self.assertRaises(OSError):
            probe_port(server.getsockname()[1])

    def test_recently_closed_connection_allows_restart(self):
        server = self.listener()
        port = server.getsockname()[1]
        with socket.create_connection(server.getsockname(), timeout=2) as client:
            connection, _ = server.accept()
            connection.close()  # Server initiates FIN, retaining server-side TIME_WAIT.
            self.assertEqual(client.recv(1), b"")
        server.close()
        # Verify this exercises lingering TCP state, rather than only an unused port.
        with socket.socket() as strict:
            with self.assertRaises(OSError):
                strict.bind(("127.0.0.1", port))
        probe_port(port)
