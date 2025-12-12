"""USB Serial reader helper.

Provides a thin wrapper around `pyserial` to read line-delimited data from
USB-to-serial devices (e.g., Arduinos, sensors). The module is defensive: if
`pyserial` is not installed, the class will raise a helpful ImportError.

Usage:
    reader = SerialReader(port='COM3', baudrate=115200)
    reader.start(callback=my_callback)
    ...
    reader.stop()
"""
from __future__ import annotations

import logging
import threading
import time
from typing import Callable, Optional

LOG = logging.getLogger(__name__)

try:
    import serial
except Exception as exc:
    serial = None  # type: ignore


class SerialReader:
    """Simple serial reader with background thread.

    The callback receives a single argument: the decoded line (str).
    """

    def __init__(self, port: str, baudrate: int = 115200, timeout: float = 1.0) -> None:
        if serial is None:
            raise ImportError("pyserial is required for SerialReader; install with 'pip install pyserial'")
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self._ser: Optional[serial.Serial] = None
        self._thread: Optional[threading.Thread] = None
        self._stop = threading.Event()

    def _open(self) -> None:
        if self._ser and self._ser.is_open:
            return
        LOG.info("Opening serial port %s @ %d", self.port, self.baudrate)
        self._ser = serial.Serial(self.port, self.baudrate, timeout=self.timeout)

    def _read_loop(self, callback: Callable[[str], None]) -> None:
        try:
            # Attempt to open the serial port and if it fails, retry until
            # `stop` is requested. This avoids crashing the background thread
            # with an uncaught SerialException when the port is not present.
            while not self._stop.is_set():
                try:
                    self._open()
                    break
                except Exception as exc:
                    LOG.warning("Could not open serial port %s: %s; retrying in 1s", self.port, exc)
                    time.sleep(1.0)

            while not self._stop.is_set():
                try:
                    if not self._ser or not self._ser.is_open:
                        # try reopening
                        self._open()
                        time.sleep(0.1)
                        continue

                    raw = self._ser.readline()  # bytes
                    if not raw:
                        continue
                    try:
                        line = raw.decode(errors='replace').strip()
                    except Exception:
                        line = str(raw)
                    callback(line)
                except Exception as exc:
                    LOG.exception("Error reading serial: %s", exc)
                    # Close serial and attempt to reopen after a pause
                    try:
                        if self._ser:
                            self._ser.close()
                    except Exception:
                        pass
                    time.sleep(1.0)
                    continue
        finally:
            try:
                if self._ser:
                    self._ser.close()
            except Exception:
                pass

    def start(self, callback: Callable[[str], None]) -> None:
        """Start background thread that calls `callback(line)` for each line read."""
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._read_loop, args=(callback,), daemon=True, name=f"SerialReader-{self.port}")
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=2.0)
