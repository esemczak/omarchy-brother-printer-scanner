import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ["QT_QUICK_CONTROLS_STYLE"] = "Basic"

import tempfile
import time
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

from PIL import Image
from PySide6.QtCore import QUrl, QThread, QObject, QPoint, QPointF, Qt, QMetaObject
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuick import QQuickWindow
from PySide6.QtTest import QTest

from brother_studio.backend import Backend
from brother_studio.theme import apply_palette

APP = QGuiApplication.instance() or QGuiApplication([])


def await_idle(backend, seconds=4):
    until = time.monotonic() + seconds
    while backend.busy and time.monotonic() < until:
        APP.processEvents()
        time.sleep(0.01)
    APP.processEvents()
    if backend.busy:
        raise AssertionError("Background worker did not finish")


class BackendTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.env = patch.dict(os.environ, {"XDG_CONFIG_HOME": self.folder.name})
        self.env.start()
        self.backend = Backend()
        self.old_palette = APP.palette()
        apply_palette(self.backend.theme)

    def tearDown(self):
        self.backend.cleanup()
        self.backend.theme_timer.stop()
        self.env.stop()
        self.folder.cleanup()
        APP.setPalette(self.old_palette)

    def test_background_completion_on_gui_thread(self):
        threads = []
        self.backend.start("Test", lambda _: 42, lambda result: threads.append((QThread.currentThread(), result)))
        await_idle(self.backend)
        self.assertEqual(threads, [(APP.thread(), 42)])

    def test_worker_errors_recover_controls(self):
        def fail(_):
            raise RuntimeError("Scanner is busy")
        self.backend.start("Scan", fail, lambda _: None)
        await_idle(self.backend)
        self.assertTrue(self.backend.error)
        self.assertEqual(self.backend.message, "Scanner is busy")
        self.assertFalse(self.backend.busy)

    def test_feeder_end_keeps_complete_pages(self):
        self.backend._device = "test scanner"
        def args(device, source, mode, dpi, size, directory, *extra):
            code = ("from PIL import Image; import sys; "
                    f"Image.new('RGB',(30,50),'white').save({str(directory / 'page-0001.png')!r}); "
                    "sys.exit(7)")
            return [sys.executable, "-c", code]
        with patch("brother_studio.backend.scan_args", args):
            self.backend.scan("ADF", "Color", 300, "A4", 0, 0)
            await_idle(self.backend)
        self.assertFalse(self.backend.error)
        self.assertEqual(len(self.backend.pages), 1)

    def test_cancellation_terminates_acquisition(self):
        self.backend._device = "test scanner"
        with patch("brother_studio.backend.scan_args", return_value=[sys.executable, "-c", "import time; time.sleep(30)"]):
            self.backend.scan("Flatbed", "Color", 300, "A4", 0, 0)
            time.sleep(0.05)
            self.backend.cancelScan()
            await_idle(self.backend)
        self.assertFalse(self.backend.error)
        self.assertEqual(self.backend.message, "Scan cancelled")
        self.assertEqual(self.backend.pages, [])

    def test_empty_feeder_reports_load_instruction(self):
        self.backend._device = "test scanner"
        with patch("brother_studio.backend.scan_args", return_value=[sys.executable, "-c", "import sys; sys.exit(7)"]):
            self.backend.scan("ADF", "Color", 300, "A4", 0, 0)
            await_idle(self.backend)
        self.assertTrue(self.backend.error)
        self.assertIn("Load the feeder", self.backend.message)

    def test_import_rotate_reorder_export(self):
        original = Path(self.folder.name) / "original.png"
        Image.new("RGB", (40, 80), "white").save(original)
        self.backend.importImage(QUrl.fromLocalFile(str(original)))
        self.backend.importImage(QUrl.fromLocalFile(str(original)))
        self.backend.rotatePage(0)
        self.assertEqual(self.backend.pages[0]["width"], 80)
        self.backend.movePage(0, 1)
        self.assertEqual(self.backend.pages[1]["width"], 80)
        target = Path(self.folder.name) / "export.pdf"
        self.backend.export(QUrl.fromLocalFile(str(target)), 0)
        await_idle(self.backend)
        self.assertTrue(target.is_file())
        self.assertIn(str(target), self.backend.recent)
        self.backend.removePage(0)
        self.assertEqual(len(self.backend.pages), 1)
        self.backend.clearPages()
        self.assertEqual(self.backend.pages, [])

    def test_queue_selection_excludes_unrelated_default(self):
        def fake(args, *extra):
            if args == ["lpstat", "-v"]:
                return "device for Unrelated: ipp://192.168.1.2/ipp/print\ndevice for Brother: ipp://192.168.1.146/ipp/print\n"
            return "Unrelated-1 user 100 date\nBrother-2 user 200 date\n"
        with patch("brother_studio.backend.command", fake):
            self.backend.refresh_printer()
            await_idle(self.backend)
        self.assertEqual(self.backend.queues, ["Brother"])
        self.assertEqual([j["id"] for j in self.backend.jobs], ["Brother-2"])

    def test_print_options_and_range_validation(self):
        self.backend._queues = [{"name": "Brother", "uri": "ipp://192.168.1.146/ipp/print"}]
        self.backend._print_file = "/tmp/file with spaces.pdf"
        calls = []
        def fake(args):
            calls.append(args)
            return "request id is Brother-3"
        with patch("brother_studio.backend.command", fake):
            self.backend.printDocument("Brother", 2, True, "A4", "1-3,5")
            await_idle(self.backend)
        self.assertIn("sides=two-sided-long-edge", calls[0])
        self.assertEqual(calls[0][-1], "/tmp/file with spaces.pdf")
        self.backend.printDocument("Brother", 1, True, "A4", "-x ; bad")
        self.assertTrue(self.backend.error)
        self.assertFalse(self.backend.busy)

    def test_qml_all_workspaces_render(self):
        engine = QQmlApplicationEngine()
        engine.rootContext().setContextProperty("studio", self.backend)
        engine.load(QUrl.fromLocalFile(str(Path(__file__).resolve().parents[1] / "brother_studio/ui/Main.qml")))
        self.assertEqual(len(engine.rootObjects()), 1)
        window = engine.rootObjects()[0]
        window.setProperty("reducedMotion", True)
        for section in range(4):
            window.setProperty("section", section)
            for _ in range(10):
                APP.processEvents()
                time.sleep(0.01)
            self.assertFalse(window.grabWindow().isNull())
        window.setProperty("closingConfirmed", True)
        window.close()

    def test_chosen_resolution_survives_start_and_progress(self):
        self.backend._online = True
        self.backend._device = "test scanner"
        engine = QQmlApplicationEngine()
        engine.rootContext().setContextProperty("studio", self.backend)
        engine.load(QUrl.fromLocalFile(str(Path(__file__).resolve().parents[1] / "brother_studio/ui/Main.qml")))
        window = engine.rootObjects()[0]
        try:
            QTest.qWait(50)
            dpi = window.findChild(QObject, "scanResolution")
            self.assertEqual(dpi.property("currentText"), "300")
            dpi.forceActiveFocus()
            QTest.keyClick(window, Qt.Key.Key_Up)
            self.assertEqual(dpi.property("currentText"), "200")
            source = window.findChild(QObject, "scanSource")
            mode = window.findChild(QObject, "scanMode")
            for control in [source, mode]:
                control.forceActiveFocus()
                QTest.keyClick(window, Qt.Key.Key_Down)
            self.assertEqual(source.property("currentText"), "ADF")
            self.assertEqual(mode.property("currentText"), "Gray")
            requested_dpi = []
            def args(device, source, mode, resolution, size, directory, *extra):
                requested_dpi.append(resolution)
                return [sys.executable, "-c", "import time; time.sleep(0.2)"]
            with patch("brother_studio.backend.scan_args", args):
                button = window.findChild(QObject, "startScan")
                point = button.mapToScene(QPointF(button.width() / 2, button.height() / 2))
                QTest.mouseClick(window, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, QPoint(round(point.x()), round(point.y())))
                self.assertEqual(requested_dpi, [200])
                self.assertTrue(self.backend.busy)
                self.assertEqual(dpi.property("currentText"), "200")
                self.backend.set_progress(0.5)
                APP.processEvents()
                self.assertEqual(dpi.property("currentText"), "200")
                await_idle(self.backend)
                self.assertEqual(dpi.property("currentText"), "200")
                self.assertEqual(source.property("currentText"), "ADF")
                self.assertEqual(mode.property("currentText"), "Gray")
        finally:
            await_idle(self.backend)
            window.setProperty("closingConfirmed", True)
            window.close()


    def test_file_selectors_use_live_palette(self):
        engine = QQmlApplicationEngine()
        engine.rootContext().setContextProperty("studio", self.backend)
        engine.load(QUrl.fromLocalFile(str(Path(__file__).resolve().parents[1] / "brother_studio/ui/Main.qml")))
        window = engine.rootObjects()[0]
        try:
            for name in ["importDialog", "exportDialog", "printDialog"]:
                dialog = window.findChild(QObject, name)
                dialog.setProperty("currentFolder", QUrl.fromLocalFile(self.folder.name))
                QMetaObject.invokeMethod(dialog, "open")
                QTest.qWait(80)
                dialog_window = next(w for w in APP.allWindows() if w.isVisible() and w.title() == dialog.property("title"))
                image = dialog_window.grabWindow()
                # The header/footer previously stayed white in a dark theme.
                self.assertEqual(image.pixelColor(10, 10).name(), self.backend.theme["surface"])
                self.assertEqual(image.pixelColor(10, image.height() - 10).name(), self.backend.theme["surface"])
                # Verify an already-open dialog updates when Omarchy switches themes.
                self.backend._theme = {**self.backend.theme, "background": "#eeeeee", "surface": "#ffffff", "foreground": "#222222", "muted": "#555555", "accent": "#2455aa"}
                apply_palette(self.backend.theme)
                self.backend.themeChanged.emit()
                QTest.qWait(40)
                image = dialog_window.grabWindow()
                self.assertEqual(image.pixelColor(10, 10).name(), "#ffffff")
                self.assertEqual(image.pixelColor(10, 100).name(), "#eeeeee")
                QMetaObject.invokeMethod(dialog, "close")
                self.backend._theme = {**self.backend.theme, "background": "#1a1b26", "surface": "#24283b", "foreground": "#c0caf5", "muted": "#9aa5ce", "accent": "#7aa2f7"}
                apply_palette(self.backend.theme)
                self.backend.themeChanged.emit()
        finally:
            window.setProperty("closingConfirmed", True)
            window.close()
            import shiboken6
            shiboken6.delete(engine)


if __name__ == "__main__":
    unittest.main()
