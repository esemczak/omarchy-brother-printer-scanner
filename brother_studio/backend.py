from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import tempfile
import threading
import time
from pathlib import Path

from PIL import Image
from PySide6.QtCore import QObject, Property, Signal, Slot, QTimer, QUrl, Qt
from PySide6.QtGui import QDesktopServices

from .core import (DEFAULT_IP, read_theme, parse_devices, option_values,
                   scan_args, printer_queues, export_pages, validate_ip)


def command(args: list[str], timeout: int = 30) -> str:
    env = os.environ.copy()
    env["LC_ALL"] = "C"
    result = subprocess.run(args, capture_output=True, text=True, timeout=timeout, env=env)
    if result.returncode:
        raise RuntimeError((result.stderr or result.stdout or "Command failed").strip()[-1200:])
    return result.stdout


class Worker(QObject):
    done = Signal(object, str)
    progress = Signal(float)

    def __init__(self, operation):
        super().__init__()
        self.operation = operation
        self.cancel = threading.Event()
        self.thread = threading.Thread(target=self.run, daemon=True)

    def run(self):
        try:
            self.done.emit(self.operation(self), "")
        except Exception as exc:
            self.done.emit(None, str(exc))


class Backend(QObject):
    changed = Signal()
    capabilitiesChanged = Signal()
    themeChanged = Signal()

    def __init__(self):
        super().__init__()
        self.settings_file = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / "brother-studio/settings.json"
        try:
            self.settings = json.loads(self.settings_file.read_text())
        except (OSError, ValueError):
            self.settings = {}
        try:
            self._ip = validate_ip(self.settings.get("ip", DEFAULT_IP))
        except (ValueError, AttributeError):
            self._ip = DEFAULT_IP
        self._theme = read_theme()
        self._busy = False
        self._operation = ""
        self._message = "Ready to connect to your Brother"
        self._error = False
        self._device = ""
        self._online = False
        self._sources = ["Flatbed", "ADF"]
        self._modes = ["Color", "Gray"]
        self._resolutions = ["100", "200", "300", "600"]
        self._pages = []
        self._queues = []
        self._jobs = []
        self._progress = 0.0
        self._last_export = ""
        self._worker = None
        self._print_file = ""
        self._recent = [x for x in self.settings.get("recent", []) if isinstance(x, str)][:12]
        self.session = Path(tempfile.mkdtemp(prefix="brother-studio-"))
        self.theme_timer = QTimer(self)
        self.theme_timer.timeout.connect(self.refresh_theme)
        self.theme_timer.start(1500)

    theme = Property("QVariantMap", lambda self: self._theme, notify=themeChanged)
    ip = Property(str, lambda self: self._ip, notify=changed)
    busy = Property(bool, lambda self: self._busy, notify=changed)
    operation = Property(str, lambda self: self._operation, notify=changed)
    message = Property(str, lambda self: self._message, notify=changed)
    error = Property(bool, lambda self: self._error, notify=changed)
    online = Property(bool, lambda self: self._online, notify=changed)
    device = Property(str, lambda self: self._device, notify=changed)
    sources = Property("QStringList", lambda self: self._sources, notify=capabilitiesChanged)
    modes = Property("QStringList", lambda self: self._modes, notify=capabilitiesChanged)
    resolutions = Property("QStringList", lambda self: self._resolutions, notify=capabilitiesChanged)
    pages = Property("QVariantList", lambda self: self._pages, notify=changed)
    queues = Property("QStringList", lambda self: [q["name"] for q in self._queues], notify=changed)
    jobs = Property("QVariantList", lambda self: self._jobs, notify=changed)
    progress = Property(float, lambda self: self._progress, notify=changed)
    printFile = Property(str, lambda self: self._print_file, notify=changed)
    recent = Property("QStringList", lambda self: self._recent, notify=changed)

    def refresh_theme(self):
        new = read_theme()
        if new != self._theme:
            self._theme = new
            self.themeChanged.emit()

    def notify(self, message: str, error: bool = False):
        self._message, self._error = message, error
        self.changed.emit()

    def save_settings(self):
        self.settings.update(ip=self._ip, recent=self._recent)
        self.settings_file.parent.mkdir(parents=True, exist_ok=True)
        temp = self.settings_file.with_suffix(".tmp")
        temp.write_text(json.dumps(self.settings, indent=2))
        temp.replace(self.settings_file)

    def start(self, name, operation, completed):
        if self._busy:
            return
        self._busy, self._operation, self._progress = True, name, 0.0
        self._error = False
        self._message = name + "…"
        worker = Worker(operation)
        self._worker = worker
        worker.progress.connect(self.set_progress)

        def done(data, error):
            self._busy, self._operation = False, ""
            self._worker = None
            if error:
                self.notify(error, True)
            else:
                try:
                    completed(data)
                except Exception as exc:
                    self.notify(str(exc), True)
            self.changed.emit()
            worker.deleteLater()

        worker.done.connect(done, Qt.ConnectionType.QueuedConnection)
        self.changed.emit()
        worker.thread.start()

    @Slot(float)
    def set_progress(self, value):
        self._progress = value
        self.changed.emit()

    @Slot()
    def discover(self):
        ip = self._ip

        def probe(worker):
            output = command(["scanimage", "-L"], 40)
            device = parse_devices(output, ip)
            if not device:
                raise RuntimeError("Scanner not found. Check power, network, and sane-airscan. Open Device for setup help.")
            help_text = command(["scanimage", "-d", device, "--help"], 40)
            return device, help_text

        def complete(result):
            self._device, help_text = result
            self._online = True
            sources = option_values(help_text, "source") or ["Flatbed"]
            modes = option_values(help_text, "mode") or ["Color", "Gray"]
            resolutions = option_values(help_text, "resolution") or ["300"]
            if (sources, modes, resolutions) != (self._sources, self._modes, self._resolutions):
                self._sources, self._modes, self._resolutions = sources, modes, resolutions
                self.capabilitiesChanged.emit()
            self.notify("Connected · Brother MFC-L2800DW")
            QTimer.singleShot(0, self.refresh_printer)

        self._online = False
        self.start("Connecting to scanner", probe, complete)

    @Slot(str)
    def setIp(self, value):
        if self._busy:
            return
        try:
            self._ip = validate_ip(value)
            self._online, self._device = False, ""
            self.save_settings()
            self.discover()
        except ValueError:
            self.notify("Enter a valid IPv4 address", True)
        except OSError as exc:
            self.notify("Could not save settings: " + str(exc), True)

    @Slot(str, str, int, str, int, int)
    def scan(self, source, mode, dpi, size, brightness, contrast):
        if not self._device:
            self.notify("Connect to your scanner first", True)
            return
        if source not in self._sources or mode not in self._modes or str(dpi) not in self._resolutions:
            self.notify("These settings are not supported by the scanner", True)
            return
        # A separate directory for each scan avoids collisions after deleting pages.
        directory = Path(tempfile.mkdtemp(prefix="scan-", dir=self.session))
        args = scan_args(self._device, source, mode, dpi, size, directory, 1, brightness, contrast)

        def acquire(worker):
            logfile = directory / "scan.log"
            env = os.environ.copy()
            env["LC_ALL"] = "C"
            started = time.monotonic()
            with logfile.open("w+") as log:
                process = subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=log, env=env)
                try:
                    while process.poll() is None:
                        if worker.cancel.wait(0.15) or time.monotonic() - started > 600:
                            process.terminate()
                            try:
                                process.wait(4)
                            except subprocess.TimeoutExpired:
                                process.kill()
                                process.wait()
                            if not worker.cancel.is_set():
                                raise RuntimeError("Scan timed out after ten minutes. Check the device.")
                            break
                        text = logfile.read_text(errors="replace")[-1500:]
                        percentages = re.findall(r"(\d+(?:\.\d+)?)%", text)
                        if percentages:
                            worker.progress.emit(min(1, float(percentages[-1]) / 100))
                finally:
                    if process.poll() is None:
                        process.kill()
                        process.wait()
            pages = []
            for path in sorted(directory.glob("page-*.png")):
                try:
                    with Image.open(path) as image:
                        image.verify()
                    pages.append((str(path), dpi))
                except (OSError, ValueError):
                    path.unlink(missing_ok=True)
            text = logfile.read_text(errors="replace")
            cancelled = worker.cancel.is_set()
            # SANE returns 7 when the feeder runs out of documents, an expected end.
            if not cancelled and process.returncode not in (0, 7):
                if pages:
                    return pages, "Some pages scanned, then the device reported: " + text[-500:]
                raise RuntimeError(text[-900:].strip() or "Scan failed")
            if not pages and not cancelled:
                raise RuntimeError("No pages scanned. Load the feeder or put a document on the glass.")
            return pages, "Scan cancelled" if cancelled else ""

        def complete(result):
            pages, warning = result
            for path, resolution in pages:
                self.add_page(Path(path), resolution)
            self._progress = 1.0 if pages else 0.0
            self.notify(warning or f"Scanned {len(pages)} page{'s' if len(pages) != 1 else ''} · ready to export", bool(warning and warning != "Scan cancelled"))

        self.start("Scanning " + ("feeder" if source == "ADF" else "flatbed"), acquire, complete)

    def add_page(self, path: Path, dpi=300):
        with Image.open(path) as image:
            w, h = image.size
        self._pages.append({"path": str(path), "url": QUrl.fromLocalFile(str(path)).toString(),
                            "width": w, "height": h, "dpi": dpi, "version": 0})

    @Slot()
    def cancelScan(self):
        if self._worker and self._operation.startswith("Scanning"):
            self._worker.cancel.set()
            self.notify("Stopping scanner…")

    @Slot(int)
    def rotatePage(self, index):
        if self._busy or not 0 <= index < len(self._pages):
            return
        page = self._pages[index]
        try:
            with Image.open(page["path"]) as image:
                image.rotate(-90, expand=True).save(page["path"], "PNG")
            page["width"], page["height"] = page["height"], page["width"]
            page["version"] += 1
            page["url"] = QUrl.fromLocalFile(page["path"]).toString() + "?v=" + str(page["version"])
            self.notify("Page rotated")
        except OSError as exc:
            self.notify(str(exc), True)

    @Slot(int)
    def removePage(self, index):
        if not self._busy and 0 <= index < len(self._pages):
            self._pages.pop(index)
            self.notify("Page removed from document")

    @Slot(int, int)
    def movePage(self, index, offset):
        target = index + offset
        if not self._busy and 0 <= index < len(self._pages) and 0 <= target < len(self._pages):
            self._pages.insert(target, self._pages.pop(index))
            self.changed.emit()

    @Slot()
    def clearPages(self):
        if not self._busy:
            self._pages = []
            self.notify("New document · ready to scan")

    @Slot(QUrl)
    def importImage(self, url):
        if self._busy:
            return
        try:
            source = Path(url.toLocalFile())
            target = self.session / f"import-{time.time_ns()}.png"
            with Image.open(source) as image:
                dpi = image.info.get("dpi", (300, 300))[0]
                image.convert("RGB").save(target, "PNG")
            self.add_page(target, round(dpi) if dpi else 300)
            self.notify("Image added to document")
        except (OSError, ValueError) as exc:
            self.notify("Cannot import image: " + str(exc), True)

    @Slot(QUrl, int)
    def export(self, url, index):
        target = Path(url.toLocalFile())
        pages = self._pages[:] if target.suffix.lower() == ".pdf" else self._pages[index:index + 1]
        if not pages:
            self.notify("Scan at least one page first", True)
            return

        def complete(_):
            self._last_export = str(target)
            self._recent = [str(target)] + [x for x in self._recent if x != str(target)]
            self._recent = self._recent[:12]
            self.save_settings()
            self.notify("Saved " + target.name)

        self.start("Exporting document", lambda _: export_pages([Path(p["path"]) for p in pages], target, pages[0]["dpi"]), complete)

    @Slot()
    def openExport(self):
        if self._last_export:
            QDesktopServices.openUrl(QUrl.fromLocalFile(self._last_export))

    @Slot(str)
    def openFile(self, path):
        if Path(path).is_file():
            QDesktopServices.openUrl(QUrl.fromLocalFile(path))
        else:
            self.notify("This file has moved or was deleted", True)

    @Slot()
    def openDevice(self):
        QDesktopServices.openUrl(QUrl("http://" + self._ip))

    @Slot()
    def openFolder(self):
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(Path.home() / "Documents")))

    @Slot(QUrl)
    def choosePrintFile(self, url):
        if url.isLocalFile() and Path(url.toLocalFile()).is_file():
            self._print_file = url.toLocalFile()
            self.changed.emit()

    @Slot()
    def refresh_printer(self):
        def query(_):
            queues = printer_queues(command(["lpstat", "-v"], 10))
            jobs = command(["lpstat", "-o"], 10)
            return queues, jobs

        def complete(result):
            queues, output = result
            # Never send a Brother document to an unrelated default printer.
            self._queues = [q for q in queues if self._ip in q["uri"] or "brother" in q["name"].lower() or "l2800" in q["uri"].lower()]
            names = [q["name"] for q in self._queues]
            self._jobs = [{"id": line.split()[0], "detail": line} for line in output.splitlines()
                          if line.split() and any(line.split()[0].startswith(n + "-") for n in names)]
            self.notify("Printer queue ready" if self._queues else "Scanner connected · add a printer queue in Device to enable printing")

        self.start("Reading printer queue", query, complete)

    @Slot(str, int, bool, str, str)
    def printDocument(self, queue, copies, duplex, paper, page_range):
        if queue not in [q["name"] for q in self._queues]:
            self.notify("Add a Brother printer queue first", True)
            return
        if not self._print_file:
            self.notify("Choose a file to print", True)
            return
        if not 1 <= copies <= 99 or paper not in ("A4", "Letter"):
            self.notify("Invalid print settings", True)
            return
        if page_range and not re.fullmatch(r"\d+(?:-\d+)?(?:,\d+(?:-\d+)?)*", page_range):
            self.notify("Use a page range like 1-3,5", True)
            return
        args = ["lp", "-d", queue, "-n", str(copies), "-o", "media=" + paper,
                "-o", "sides=" + ("two-sided-long-edge" if duplex else "one-sided")]
        if page_range:
            args += ["-P", page_range]
        args += ["--", self._print_file]
        self.start("Sending to printer", lambda _: command(args), lambda text: self.notify(text.strip()))

    @Slot(str)
    def cancelJob(self, job_id):
        if job_id not in [job["id"] for job in self._jobs]:
            return
        def complete(_):
            self.notify("Print job cancelled")
            QTimer.singleShot(0, self.refresh_printer)
        self.start("Cancelling print job", lambda _: command(["cancel", job_id]), complete)

    @Slot()
    def setupPrinter(self):
        # Authentication is handled by the desktop's polkit agent, never a shell.
        ip = self._ip
        def setup(_):
            command(["pkexec", "/usr/bin/systemctl", "enable", "--now", "cups.service"], 120)
            command(["pkexec", "/usr/bin/lpadmin", "-p", "Brother_MFC_L2800DW", "-E",
                     "-v", f"ipp://{ip}/ipp/print", "-m", "everywhere"], 120)
        def complete(_):
            self.notify("Brother printer added")
            QTimer.singleShot(0, self.refresh_printer)
        self.start("Setting up printer · desktop authentication may be required", setup, complete)

    @Slot()
    def useScanForPrint(self):
        pages = self._pages[:]
        target = self.session / "print-document.pdf"
        def complete(_):
            self._print_file = str(target)
            self.notify("Scanned document ready in Print")
        self.start("Preparing scanned document", lambda _: export_pages([Path(p["path"]) for p in pages], target, pages[0]["dpi"] if pages else 300), complete)

    def cleanup(self):
        if self._worker:
            self._worker.cancel.set()
            # Scan acquisition sees cancellation within 150ms; avoid deleting its output early.
            self._worker.thread.join(5)
            if self._worker.thread.is_alive():
                return
        shutil.rmtree(self.session, ignore_errors=True)
