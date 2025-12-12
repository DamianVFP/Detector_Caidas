"""Controller for a generic IP speaker.

This module provides a small, generic wrapper to interact with IP-enabled
speakers that expose simple HTTP endpoints. Implementations vary by device;
this wrapper uses a conservative approach:

- `IpSpeaker(host)` where `host` is e.g. "http://10.0.0.5:5000" or "http://10.0.0.5"
- `speaker.play_url(mp3_url)` attempts to instruct the speaker to play an MP3 URL
- `speaker.set_volume(level)` sets volume if supported
- `speaker.ping()` checks reachability

If your speaker uses a different API (UPnP/DLNA/Chromecast), adapt this
module or use an external library (e.g., `pychromecast`, `coherence`, `soco`).
"""
from __future__ import annotations

import logging
from typing import Optional

import requests

LOG = logging.getLogger(__name__)


class IpSpeaker:
    """Minimal controller for HTTP-capable IP speakers.

    This is intentionally generic. Many DIY IP speaker servers expose
    endpoints such as `/play?url=...` or `/volume?level=...`. You can
    override `play_url` if your device requires a different payload.
    """

    def __init__(self, host: str, timeout: float = 3.0) -> None:
        self.host = host.rstrip("/")
        self.timeout = timeout

    def _url(self, path: str) -> str:
        return f"{self.host}/{path.lstrip('/') }"

    def ping(self) -> bool:
        try:
            r = requests.get(self.host, timeout=self.timeout)
            r.raise_for_status()
            return True
        except Exception as exc:
            LOG.debug("Ping failed to %s: %s", self.host, exc)
            return False

    def play_url(self, mp3_url: str) -> bool:
        """Attempt to instruct device to play remote MP3/stream URL.

        Tries common endpoints in order; returns True if one succeeded.
        """
        candidates = [
            self._url(f"play?url={mp3_url}"),
            self._url("play"),
            self._url("/play"),
        ]

        # Try GET with query
        try:
            r = requests.get(candidates[0], timeout=self.timeout)
            if r.status_code // 100 == 2:
                return True
        except Exception:
            pass

        # Try POST to /play with JSON body
        try:
            r = requests.post(self._url("play"), json={"url": mp3_url}, timeout=self.timeout)
            if r.status_code // 100 == 2:
                return True
        except Exception:
            pass

        LOG.warning("play_url: device did not accept known play endpoints")
        return False

    def set_volume(self, level: int) -> bool:
        """Set volume (0-100). Returns True on success or False if unsupported."""
        level = max(0, min(100, int(level)))
        try:
            r = requests.post(self._url("volume"), json={"level": level}, timeout=self.timeout)
            if r.status_code // 100 == 2:
                return True
        except Exception:
            pass
        try:
            r = requests.get(self._url(f"volume?level={level}"), timeout=self.timeout)
            if r.status_code // 100 == 2:
                return True
        except Exception:
            pass

        LOG.debug("set_volume: not supported by device")
        return False
