"""Chrome native messaging host for the AI Usage Monitor extension.

Chrome starts this process when the extension connects and keeps it alive while
the connection is open. It writes the usage data it receives to usage.json and
forwards refresh requests from the widget back to the extension.

The named event doubles as a liveness signal: it exists only while this process
runs, so the widget can tell whether Chrome is connected.
"""
import ctypes
import json
import os
import struct
import sys
import threading
import time
import traceback
from ctypes import wintypes
from pathlib import Path

DATA_DIR = Path(os.environ["LOCALAPPDATA"]) / "AIUsageWidget"
USAGE_FILE = DATA_DIR / "usage.json"
LOG_FILE = DATA_DIR / "host.log"
REFRESH_EVENT = "Local\\AIUsageWidget.Refresh"  # must match widget/winapi.py

kernel32 = ctypes.windll.kernel32
kernel32.CreateEventW.argtypes = [ctypes.c_void_p, wintypes.BOOL, wintypes.BOOL, wintypes.LPCWSTR]
kernel32.CreateEventW.restype = wintypes.HANDLE
kernel32.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
INFINITE, WAIT_OBJECT_0 = 0xFFFFFFFF, 0


def read_message(stream):
    header = stream.read(4)
    if len(header) < 4:
        return None  # Chrome closed the connection
    (length,) = struct.unpack("<I", header)
    return json.loads(stream.read(length).decode("utf-8"))


def send(message):
    data = json.dumps(message).encode("utf-8")
    sys.stdout.buffer.write(struct.pack("<I", len(data)) + data)
    sys.stdout.buffer.flush()


def save_usage(usage):
    tmp = USAGE_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(usage, ensure_ascii=False), encoding="utf-8")
    for _ in range(10):
        try:
            os.replace(tmp, USAGE_FILE)
            return
        except PermissionError:  # the widget is reading the file at this instant
            time.sleep(0.05)
    raise PermissionError(f"could not replace {USAGE_FILE}")


def relay_refresh_requests(event):
    while kernel32.WaitForSingleObject(event, INFINITE) == WAIT_OBJECT_0:
        send({"type": "refresh"})


def main():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    event = kernel32.CreateEventW(None, False, False, REFRESH_EVENT)
    threading.Thread(target=relay_refresh_requests, args=(event,), daemon=True).start()
    while (msg := read_message(sys.stdin.buffer)) is not None:
        if msg.get("type") == "usage":
            save_usage(msg["usage"])


if __name__ == "__main__":
    try:
        main()
    except Exception:
        with LOG_FILE.open("a", encoding="utf-8") as log:
            log.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')}\n{traceback.format_exc()}\n")
        raise
