import tempfile
import unittest
from pathlib import Path

from PIL import Image

from brother_studio.core import (validate_ip, read_theme, parse_devices, option_values,
                                 scan_args, export_pages, printer_queues)


class CoreTests(unittest.TestCase):
    def test_ip_is_validated(self):
        self.assertEqual(validate_ip(" 192.168.1.146 "), "192.168.1.146")
        for bad in [";touch /tmp/oops", "https://192.168.1.146", "256.1.1.1", "localhost"]:
            with self.assertRaises(ValueError):
                validate_ip(bad)

    def test_device_matches_address_not_another_brother(self):
        text = ("device `airscan:e0:Brother MFC-L2800DW' is a eSCL Brother ip=192.168.1.147\n"
                "device `escl:https://192.168.1.146:443' is a Brother\n"
                "device `airscan:e1:Brother MFC-L2800DW' is a eSCL Brother ip=192.168.1.146\n")
        self.assertEqual(parse_devices(text, "192.168.1.146"), "airscan:e1:Brother MFC-L2800DW")
        self.assertEqual(parse_devices(text, "192.168.1.14"), "")

    def test_capability_options(self):
        text = "    --source Flatbed|ADF [Flatbed]\n    --resolution 100|200|300|600dpi [300]\n    --mode Color|Gray [Color]\n"
        self.assertEqual(option_values(text, "source"), ["Flatbed", "ADF"])
        self.assertEqual(option_values(text, "resolution"), ["100", "200", "300", "600"])
        self.assertEqual(option_values(text, "mode"), ["Color", "Gray"])

    def test_flatbed_and_feeder_commands(self):
        args = scan_args("device name", "Flatbed", "Color", 300, "A4", Path("/tmp/path with spaces"), 1)
        self.assertIn("--batch-count=1", args)
        self.assertIn("--batch=/tmp/path with spaces/page-%04d.png", args)
        self.assertIn("296.9", args)
        feeder = scan_args("device", "ADF", "Gray", 600, "Maximum", Path("/tmp"), 1)
        self.assertNotIn("--batch-count=1", feeder)
        self.assertNotIn("-y", feeder)

    def test_modern_omarchy_palette_and_live_read(self):
        with tempfile.TemporaryDirectory() as folder:
            home = Path(folder)
            root = home / ".local/state/omarchy/current"
            (root / "theme").mkdir(parents=True)
            (root / "theme.name").write_text("catppuccin")
            palette = root / "theme/colors.toml"
            palette.write_text('background = "#112233"\nforeground = "#ddeeff"\naccent = "#cc44aa"\ngreen = "#abcdef"\nlighter_background = "#223344"\n')
            result = read_theme(home)
            self.assertEqual(result["themeName"], "Catppuccin")
            self.assertEqual(result["surface"], "#223344")
            self.assertEqual(result["green"], "#abcdef")
            palette.write_text('accent = "#778899"\n')
            self.assertEqual(read_theme(home)["accent"], "#778899")

    def test_legacy_theme(self):
        with tempfile.TemporaryDirectory() as folder:
            home = Path(folder)
            root = home / ".config/omarchy/current/theme"
            root.mkdir(parents=True)
            (root / "alacritty.toml").write_text('[colors.primary]\nbackground = "#123456"\nforeground = "#ffffff"\n[colors.normal]\nblue = "#aabbcc"\n')
            self.assertEqual(read_theme(home)["background"], "#123456")

    def test_multipage_export_and_atomic_failure(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            pages = []
            for i in range(2):
                path = root / f"page-{i}.png"
                Image.new("RGB", (40, 60), "white").save(path)
                pages.append(path)
            target = root / "document.pdf"
            export_pages(pages, target)
            content = target.read_bytes()
            self.assertTrue(content.startswith(b"%PDF"))
            self.assertIn(b"/Count 2", content)
            target.write_bytes(b"existing document")
            with self.assertRaises(FileNotFoundError):
                export_pages([root / "missing.png"], target)
            self.assertEqual(target.read_bytes(), b"existing document")
            with self.assertRaises(ValueError):
                export_pages(pages, root / "image.png")
            export_pages(pages[:1], root / "image.png")
            with Image.open(root / "image.png") as image:
                self.assertEqual(image.size, (40, 60))

    def test_queue_parsing(self):
        self.assertEqual(printer_queues("device for Brother: ipp://192.168.1.146/ipp/print\n"),
                         [{"name": "Brother", "uri": "ipp://192.168.1.146/ipp/print"}])


if __name__ == "__main__":
    unittest.main()
