import os
import select
import sys
import termios
import threading
import tty

import cv2


class KeyListener:
    """Edge-triggered keyboard listener that reads stdin in a background thread.

    Each physical keypress is consumable exactly once via consume_pressed(key).
    Use as a context manager so the terminal mode is restored on exit.
    Gracefully no-ops if stdin is not a TTY.

    Example:
        with KeyListener() as keys:
            while running:
                if keys.consume_pressed("s"):    recorder.start()
                if keys.consume_pressed("e"):    recorder.stop()
                if keys.consume_pressed("esc"):  running = False
    """

    def __init__(self):
        self._pressed = set()
        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self._thread = None
        self._old_settings = None
        self._fd = None

    def start(self):
        if not sys.stdin.isatty():
            print("[KeyListener] stdin is not a TTY; key input disabled.")
            return
        self._fd = sys.stdin.fileno()
        self._old_settings = termios.tcgetattr(self._fd)
        tty.setcbreak(self._fd)
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=1.0)
            self._thread = None
        if self._old_settings is not None:
            termios.tcsetattr(self._fd, termios.TCSADRAIN, self._old_settings)
            self._old_settings = None
            self._fd = None

    def consume_pressed(self, key):
        with self._lock:
            if key in self._pressed:
                self._pressed.remove(key)
                return True
            return False

    def _loop(self):
        while not self._stop_event.is_set():
            r, _, _ = select.select([self._fd], [], [], 0.1)
            if not r:
                continue
            ch = os.read(self._fd, 1).decode(errors="ignore")
            if ch == "\x1b":
                # Distinguish bare ESC from escape sequences (arrow keys etc.)
                r2, _, _ = select.select([self._fd], [], [], 0.01)
                if r2:
                    os.read(self._fd, 4)  # drain rest of escape sequence
                    continue
                name = "esc"
            else:
                name = ch
            with self._lock:
                self._pressed.add(name)

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, *args):
        self.stop()


def draw_overlays(image, overlays):
    copied = image.copy()
    for item in overlays:
        if item["type"] == "dot" and item.get("xy") is not None:
            cv2.circle(
                copied,
                (int(item["xy"][0]), int(item["xy"][1])),
                item.get("radius", 6),
                item.get("color", (0, 255, 0)),
                -1,
            )
        elif item["type"] == "text":
            cv2.putText(
                copied,
                text=item["content"],
                org=item.get("position", [50, 50]),
                color=item.get("color", (0, 0, 255)),
                fontFace=cv2.FONT_HERSHEY_SIMPLEX,
                fontScale=1,
                thickness=3,
            )
    return copied