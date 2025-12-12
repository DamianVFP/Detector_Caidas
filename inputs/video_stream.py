"""Video stream helper.

Provides a `VideoStream` class that accepts a webcam index or a URL (IP camera)
and exposes a resilient `read()` method with automatic reconnection.

Usage:
    from inputs.video_stream import VideoStream
    stream = VideoStream(source)
    with stream:
        ok, frame = stream.read()
        if ok: ...
"""
from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Optional, Tuple, Union

import cv2

LOG = logging.getLogger(__name__)


class VideoStream:
    """Wrapper around cv2.VideoCapture with reconnection logic.

    Args:
        source: int for webcam index (0,1,..) or string URL (http://.../video)
        reconnect_attempts: number of times to try reconnecting before giving up
        reconnect_delay: seconds to wait between reconnect attempts (exponential backoff)
    """

    def __init__(self, source: Union[int, str] = 0, reconnect_attempts: int = 5, reconnect_delay: float = 1.0):
        self._raw_source = source
        # Convert numeric string to int when appropriate
        if isinstance(source, str) and source.isdigit():
            try:
                self.source: Union[int, str] = int(source)
            except Exception:
                self.source = source
        else:
            self.source = source

        self.reconnect_attempts = reconnect_attempts
        self.reconnect_delay = reconnect_delay
        self._cap: Optional[cv2.VideoCapture] = None
        self._opened = False

    def open(self) -> bool:
        """Open the capture device/URL. Returns True on success."""
        self.close()
        LOG.info("Opening video source: %s", self.source)
        self._cap = cv2.VideoCapture(self.source)
        # Small delay to allow stream to initialize
        time.sleep(0.2)
        self._opened = bool(self._cap and self._cap.isOpened())
        if not self._opened:
            LOG.warning("Failed to open video source: %s", self.source)
        return self._opened

    def close(self) -> None:
        if self._cap is not None:
            try:
                self._cap.release()
            except Exception:
                pass
        self._cap = None
        self._opened = False

    def read(self) -> Tuple[bool, Optional[any]]:
        """Read a frame from the stream. If the stream is lost, attempts to reconnect.

        Returns (ok, frame). If ok is False, frame is None.
        """
        if self._cap is None or not self._opened:
            opened = self.open()
            if not opened:
                return False, None

        ok, frame = False, None
        try:
            ok, frame = self._cap.read()
        except Exception as exc:
            LOG.exception("Exception reading frame: %s", exc)
            ok = False

        if not ok or frame is None:
            # Attempt reconnection
            LOG.warning("Frame read failed, attempting reconnection to %s", self.source)
            success = False
            delay = self.reconnect_delay
            for attempt in range(1, self.reconnect_attempts + 1):
                LOG.info("Reconnection attempt %d/%d (delay %.1fs)", attempt, self.reconnect_attempts, delay)
                time.sleep(delay)
                try:
                    self.open()
                    if self._cap is not None:
                        ok, frame = self._cap.read()
                        if ok and frame is not None:
                            success = True
                            break
                except Exception:
                    pass
                delay = min(delay * 2, 10.0)

            if not success:
                LOG.error("Unable to reconnect to video source after %d attempts", self.reconnect_attempts)
                return False, None

        return True, frame

    # Context manager support
    def __enter__(self) -> "VideoStream":
        self.open()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()


def create_from_config(source_env: Optional[str] = None) -> VideoStream:
    """Helper to create VideoStream from config-style string.

    If `source_env` is numeric string, it will be converted to int.
    """
    src = source_env
    if src is None:
        src = "0"
    if isinstance(src, str) and src.isdigit():
        src_val = int(src)
    else:
        src_val = src
    return VideoStream(src_val)
