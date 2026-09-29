from __future__ import annotations

import ipaddress
import re
import tomllib
from pathlib import Path

DEFAULT_IP = "192.168.1.146"
DEFAULT_PALETTE = {
    "background": "#1a1b26", "surface": "#24283b", "foreground": "#c0caf5",
    "muted": "#9aa5ce", "accent": "#7aa2f7", "green": "#9ece6a",
    "red": "#f7768e", "border": "#414868", "themeName": "Tokyo Night",
}


def validate_ip(value: str) -> str:
    return str(ipaddress.IPv4Address(value.strip()))


def theme_paths(home: Path | None = None) -> list[Path]:
    home = home or Path.home()
    return [home / ".local/state/omarchy/current", home / ".config/omarchy/current"]


def read_theme(home: Path | None = None) -> dict:
    palette = DEFAULT_PALETTE.copy()
    for root in theme_paths(home):
        try:
            name = (root / "theme.name").read_text().strip()
            palette["themeName"] = name.replace("-", " ").title()
        except OSError:
            pass
        try:
            data = tomllib.loads((root / "theme/colors.toml").read_text())
            values = {k: v for k, v in data.items() if isinstance(v, str)}
            mapping = {"background": ["background"], "foreground": ["foreground"],
                       "accent": ["accent", "blue", "color4"], "green": ["green", "color2"],
                       "red": ["red", "color1"], "muted": ["light_foreground", "foreground", "color7"],
                       "surface": ["lighter_background", "color0", "background"],
                       "border": ["muted", "color8"]}
            for dest, sources in mapping.items():
                value = next((values[src] for src in sources if src in values), "")
                if re.fullmatch(r"#[0-9a-fA-F]{6}", value):
                    palette[dest] = value
            return palette
        except (OSError, ValueError):
            pass
        try:
            data = tomllib.loads((root / "theme/alacritty.toml").read_text())["colors"]
            primary, normal = data.get("primary", {}), data.get("normal", {})
            for dest, value in {
                "background": primary.get("background"), "foreground": primary.get("foreground"),
                "accent": normal.get("blue"), "green": normal.get("green"),
                "red": normal.get("red"), "surface": normal.get("black"),
                "muted": data.get("bright", {}).get("black"),
            }.items():
                if isinstance(value, str) and re.fullmatch(r"#[0-9a-fA-F]{6}", value):
                    palette[dest] = value
            return palette
        except (OSError, ValueError, KeyError):
            pass
    return palette


def parse_devices(output: str, ip: str) -> str:
    entries = re.findall(r"device [`']([^']+)'([^\n]*)", output)
    devices = [entry[0] for entry in entries]
    # sane-airscan correctly negotiates this Brother's protocol and ADF batches.
    for device, description in entries:
        if device.startswith("airscan:") and re.search(r"ip=" + re.escape(ip) + r"(?=\s|$)", description):
            return device
    # Prefer deterministic IP-based devices, otherwise the discovered model.
    for device in devices:
        if re.search(r"(?<![\d.])" + re.escape(ip) + r"(?![\d.])", device):
            return device
    return ""


def option_values(help_text: str, option: str) -> list[str]:
    match = re.search(r"^\s+--" + re.escape(option) + r"\s+(.+?)\s+\[", help_text, re.M)
    if not match:
        return []
    return [x.strip().removesuffix("dpi") for x in match.group(1).split("|")]


def scan_args(device: str, source: str, mode: str, dpi: int, size: str,
              directory: Path, start: int, brightness: int = 0, contrast: int = 0) -> list[str]:
    if source not in ("Flatbed", "ADF") or mode not in ("Color", "Gray", "Lineart"):
        raise ValueError("Unsupported scanner setting")
    if dpi not in (100, 200, 300, 600):
        raise ValueError("Unsupported resolution")
    args = ["scanimage", "-d", device, "--format=png", "--progress",
            f"--source={source}", f"--mode={mode}", f"--resolution={dpi}",
            f"--batch={directory / 'page-%04d.png'}", f"--batch-start={start}"]
    if source == "Flatbed":
        args.append("--batch-count=1")
    # Scanner glass is slightly shorter than nominal A4 (reported by this model).
    dimensions = {"A4": (210, 296.9), "Letter": (215.9, 279.4)}
    if size in dimensions:
        w, h = dimensions[size]
        args += ["-x", str(w), "-y", str(h)]
    elif size != "Maximum":
        raise ValueError("Unknown page size")
    args += [f"--brightness={max(-100, min(100, brightness))}",
             f"--contrast={max(-100, min(100, contrast))}"]
    return args


def printer_queues(output: str) -> list[dict]:
    queues = []
    for line in output.splitlines():
        match = re.match(r"device for ([^:]+): (.+)", line)
        if match:
            queues.append({"name": match[1], "uri": match[2]})
    return queues


def export_pages(paths: list[Path], target: Path, dpi: int = 300) -> None:
    """Write atomically so a failed export never destroys an existing document."""
    import os
    import tempfile
    from PIL import Image
    images = []
    temp_name = None
    try:
        for path in paths:
            with Image.open(path) as image:
                images.append(image.convert("RGB"))
        if not images:
            raise ValueError("Scan or import at least one page first")
        fmt = target.suffix.lower()
        if fmt not in (".pdf", ".png", ".jpg", ".jpeg"):
            raise ValueError("Choose PDF, PNG or JPEG")
        if fmt != ".pdf" and len(images) != 1:
            raise ValueError("Select one page for an image export, or choose PDF for all pages")
        target.parent.mkdir(parents=True, exist_ok=True)
        fd, temp_name = tempfile.mkstemp(prefix=".brother-export-", dir=target.parent)
        os.close(fd)
        if fmt == ".pdf":
            images[0].save(temp_name, "PDF", save_all=True, append_images=images[1:], resolution=dpi)
        else:
            images[0].save(temp_name, "PNG" if fmt == ".png" else "JPEG", dpi=(dpi, dpi))
        os.replace(temp_name, target)
        temp_name = None
    finally:
        for image in images:
            image.close()
        if temp_name:
            Path(temp_name).unlink(missing_ok=True)
