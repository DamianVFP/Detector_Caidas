"""ESP32 client helpers.

Provides two simple connectivity options to talk with an ESP32 device:

- MQTTClient: uses `paho.mqtt.client` if available (recommended when ESP32
  runs an MQTT client or you have an MQTT broker like Mosquitto).
- TcpClient: very small TCP socket client for simple message exchange if the
  ESP32 runs a TCP server.

Both classes expose callbacks for incoming messages.
"""
from __future__ import annotations

import logging
import socket
import threading
from typing import Callable, Optional

LOG = logging.getLogger(__name__)

try:
    import paho.mqtt.client as mqtt
except Exception:
    mqtt = None  # type: ignore


class MQTTClient:
    """Simple MQTT wrapper. Requires `paho-mqtt`.

    Usage:
        client = MQTTClient(broker='192.168.1.10', port=1883, topic='esp32/topic')
        client.start(on_message=my_callback)
        client.publish('hello')
        client.stop()
    """

    def __init__(self, broker: str = 'localhost', port: int = 1883, topic: str = 'esp32') -> None:
        if mqtt is None:
            raise ImportError("paho-mqtt is required for MQTTClient; install with 'pip install paho-mqtt'")
        self.broker = broker
        self.port = port
        self.topic = topic
        self._client = mqtt.Client()
        self._on_message: Optional[Callable[[str], None]] = None

    def _internal_on_message(self, client, userdata, msg):
        payload = msg.payload.decode(errors='replace')
        LOG.debug("MQTT message on %s: %s", msg.topic, payload)
        if self._on_message:
            self._on_message(payload)

    def start(self, on_message: Callable[[str], None]) -> None:
        self._on_message = on_message
        self._client.on_message = self._internal_on_message
        self._client.connect(self.broker, self.port)
        self._client.loop_start()
        self._client.subscribe(self.topic)

    def publish(self, payload: str) -> None:
        self._client.publish(self.topic, payload)

    def stop(self) -> None:
        try:
            self._client.loop_stop()
            self._client.disconnect()
        except Exception:
            pass


class TcpClient:
    """Simple TCP client for ESP32 servers.

    Usage:
        c = TcpClient('192.168.1.50', 9000)
        c.start(on_message)
        c.send('hello')
        c.stop()
    """

    def __init__(self, host: str, port: int = 9000) -> None:
        self.host = host
        self.port = port
        self._sock: Optional[socket.socket] = None
        self._thread: Optional[threading.Thread] = None
        self._stop = threading.Event()
        self._on_message: Optional[Callable[[str], None]] = None

    def _recv_loop(self) -> None:
        try:
            self._sock = socket.create_connection((self.host, self.port), timeout=5)
            with self._sock:
                while not self._stop.is_set():
                    data = self._sock.recv(1024)
                    if not data:
                        break
                    try:
                        text = data.decode(errors='replace')
                    except Exception:
                        text = str(data)
                    if self._on_message:
                        self._on_message(text)
        except Exception as exc:
            LOG.exception("TcpClient error: %s", exc)

    def start(self, on_message: Callable[[str], None]) -> None:
        self._on_message = on_message
        self._stop.clear()
        self._thread = threading.Thread(target=self._recv_loop, daemon=True)
        self._thread.start()

    def send(self, text: str) -> None:
        try:
            if self._sock:
                self._sock.sendall(text.encode())
        except Exception:
            LOG.exception("Error sending to ESP32")

    def stop(self) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=2.0)
