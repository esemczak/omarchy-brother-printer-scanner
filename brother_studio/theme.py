"""Apply Omarchy colours to every Qt control, including separate dialog windows."""
from PySide6.QtGui import QColor, QGuiApplication, QPalette


def apply_palette(theme: dict) -> None:
    palette = QPalette()
    bg = QColor(theme["background"])
    surface = QColor(theme["surface"])
    fg = QColor(theme["foreground"])
    muted = QColor(theme["muted"])
    accent = QColor(theme["accent"])
    roles = {
        QPalette.ColorRole.Window: bg,
        QPalette.ColorRole.WindowText: fg,
        QPalette.ColorRole.Base: surface,
        QPalette.ColorRole.AlternateBase: bg,
        QPalette.ColorRole.Text: fg,
        QPalette.ColorRole.Button: surface,
        QPalette.ColorRole.ButtonText: fg,
        QPalette.ColorRole.ToolTipBase: surface,
        QPalette.ColorRole.ToolTipText: fg,
        QPalette.ColorRole.Highlight: accent,
        QPalette.ColorRole.HighlightedText: fg,
        QPalette.ColorRole.PlaceholderText: muted,
        QPalette.ColorRole.Link: accent,
        QPalette.ColorRole.LinkVisited: accent,
        QPalette.ColorRole.Light: surface.lighter(140),
        QPalette.ColorRole.Midlight: surface.lighter(120),
        QPalette.ColorRole.Mid: QColor(theme["border"]),
        QPalette.ColorRole.Dark: bg.darker(130),
        QPalette.ColorRole.Shadow: bg.darker(160),
        QPalette.ColorRole.BrightText: fg,
        QPalette.ColorRole.Accent: accent,
    }
    for role, color in roles.items():
        palette.setColor(QPalette.ColorGroup.All, role, color)
    disabled = QColor.fromRgbF((fg.redF() + bg.redF()) / 2,
                              (fg.greenF() + bg.greenF()) / 2,
                              (fg.blueF() + bg.blueF()) / 2)
    for role in (QPalette.ColorRole.Text, QPalette.ColorRole.WindowText,
                 QPalette.ColorRole.ButtonText):
        palette.setColor(QPalette.ColorGroup.Disabled, role, disabled)
    QGuiApplication.setPalette(palette)
