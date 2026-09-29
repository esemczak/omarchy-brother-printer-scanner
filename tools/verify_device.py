"""Read-only discovery, optionally acquire a low-resolution flatbed test scan."""
import argparse
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QTimer, QUrl
from PySide6.QtGui import QGuiApplication
from brother_studio.backend import Backend

parser = argparse.ArgumentParser()
parser.add_argument("--scan", action="store_true", help="Test flatbed scanning at 100 DPI")
args = parser.parse_args()
app = QGuiApplication([])
backend = Backend()
stage = "discover"
started = time.monotonic()
result = 1


def check():
    global stage, result
    if time.monotonic() - started > 120:
        print("Hardware check timed out", flush=True)
        app.quit()
        return
    if backend.busy:
        return
    if stage == "discover":
        if not backend.online:
            print("Discovery failed:", backend.message, flush=True)
            app.quit()
            return
        print("Connected:", backend.device, flush=True)
        print("Sources:", backend.sources, "Modes:", backend.modes, "DPI:", backend.resolutions, flush=True)
        print("Printer queues:", backend.queues, flush=True)
        if not args.scan:
            result = 0
            app.quit()
            return
        stage = "scan"
        backend.scan("Flatbed", "Color", 100, "A4", 0, 0)
    elif stage == "scan":
        if backend.error or len(backend.pages) != 1:
            print("Scan failed:", backend.message, flush=True)
            app.quit()
            return
        page = backend.pages[0]
        print("Scanned:", page["width"], "x", page["height"], "pixels", flush=True)
        stage = "export"
        backend.export(QUrl.fromLocalFile("/tmp/brother-studio-hardware-test.pdf"), 0)
    elif stage == "export":
        if backend.error:
            print("Export failed:", backend.message, flush=True)
        else:
            print("Exported: /tmp/brother-studio-hardware-test.pdf", flush=True)
            result = 0
        app.quit()


timer = QTimer()
timer.timeout.connect(check)
timer.start(250)
QTimer.singleShot(0, backend.discover)
app.aboutToQuit.connect(backend.cleanup)
app.exec()
sys.exit(result)
