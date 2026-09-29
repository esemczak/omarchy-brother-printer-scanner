import os
import sys
from pathlib import Path

from PySide6.QtCore import QUrl, QTimer
from PySide6.QtGui import QGuiApplication, QIcon
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuick import QQuickWindow

from .backend import Backend
from .theme import apply_palette


def main():
    os.environ["QT_QUICK_CONTROLS_STYLE"] = "Basic"
    app = QGuiApplication(sys.argv)
    app.setApplicationName("Brother Studio")
    app.setOrganizationName("BrotherStudio")
    app.setDesktopFileName("brother-studio")
    root = Path(__file__).resolve().parent
    app.setWindowIcon(QIcon(str(root.parent / "assets/brother-studio.svg")))
    backend = Backend()
    apply_palette(backend.theme)
    backend.themeChanged.connect(lambda: apply_palette(backend.theme))
    engine = QQmlApplicationEngine()
    engine.rootContext().setContextProperty("studio", backend)
    engine.load(QUrl.fromLocalFile(str(root / "ui/Main.qml")))
    if not engine.rootObjects():
        return 1
    app.aboutToQuit.connect(backend.cleanup)
    # --smoke exercises QML loading without accessing hardware or writing preferences.
    if "--smoke" in sys.argv:
        def capture():
            try:
                engine.rootObjects()[0].grabWindow().save("/tmp/brother-studio-preview.png")
            finally:
                app.quit()
        QTimer.singleShot(800, capture)
    else:
        QTimer.singleShot(300, backend.discover)
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
