"""
Raw TCP socket client for the Freenove Pico W robot.

The Pico W runs a TCP server on port 4002 (sketch 06.2_Multi_Functional_Car).
All commands are ASCII strings terminated with '\n', fields separated by '#'.
"""

import socket
import sys
import threading
from typing import Optional


class RobotClient:
    """Low-level TCP client. Use RobotController for high-level commands."""

    DEFAULT_PORT = 4002
    BUFFER_SIZE  = 1024

    def __init__(self, host: str, port: int = DEFAULT_PORT, timeout: float = 5.0):
        self.host    = host
        self.port    = port
        self.timeout = timeout
        self._socket: Optional[socket.socket] = None
        self._lock   = threading.Lock()

    # ── Connection ──────────────────────────────────────────────────────────

    def connect(self) -> None:
        """Open a TCP connection to the robot."""
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._socket.settimeout(self.timeout)
        self._socket.connect((self.host, self.port))
        print(f"Connected to robot at {self.host}:{self.port}", file=sys.stderr)

    def disconnect(self) -> None:
        """Close the TCP connection."""
        if self._socket:
            try:
                self._socket.close()
            except OSError:
                pass
            self._socket = None
            print("Disconnected from robot", file=sys.stderr)

    def is_connected(self) -> bool:
        return self._socket is not None

    # ── I/O ─────────────────────────────────────────────────────────────────

    def send(self, command: str) -> None:
        """Send a raw command string (must end with '\\n')."""
        if not self._socket:
            raise ConnectionError("Not connected — call connect() first.")
        with self._lock:
            self._socket.sendall(command.encode("utf-8"))

    def send_and_receive(self, command: str, expect_prefix: str = "") -> str:
        """Send a command and return the robot's response.

        The Pico W pushes unsolicited messages on the same socket (e.g. 'A#2\\n'
        on connect, 'P#<voltage>\\n' every 3 s).  If expect_prefix is given we
        discard lines that don't start with it so those background messages can't
        swallow the real reply.
        """
        self.send(command)
        deadline = socket.getdefaulttimeout() or self.timeout
        import time as _time
        start = _time.monotonic()
        buf = ""
        with self._lock:
            try:
                while _time.monotonic() - start < deadline:
                    chunk = self._socket.recv(self.BUFFER_SIZE)
                    if not chunk:
                        break
                    buf += chunk.decode("utf-8")
                    # Check each complete line we've accumulated
                    while "\n" in buf:
                        line, buf = buf.split("\n", 1)
                        line = line.strip()
                        if not line:
                            continue
                        if not expect_prefix or line.startswith(expect_prefix):
                            return line
                        # discard unsolicited line, keep reading
            except socket.timeout:
                pass
        return ""

    # ── Context manager ──────────────────────────────────────────────────────

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, *args):
        self.disconnect()
