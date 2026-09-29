# Brother Studio

A native Qt Quick app for a Brother MFC-L2800DW on an Omarchy desktop.
The configured address is **192.168.1.146**. Documents stay local.

## Run

```sh
./setup.sh
./run.sh
```

Qt/Python dependencies are isolated in `.venv`. System prerequisites on Omarchy:

```sh
omarchy pkg add sane sane-airscan cups
```

Add an application launcher entry with `./install.sh`. Keep this checkout in place;
the launcher points to its `run.sh`. Remove the entry by deleting
`~/.local/share/applications/brother-studio.desktop` and the matching icon.

## Scan

Connect, choose flatbed or ADF, colour or grayscale, resolution and page size.
Place flatbed originals face down; load the feeder face up. ADF scans all loaded
pages until it is empty. **This model does not have automatic duplex scanning.**
Scan another pass for reverse sides and reorder the thumbnails with the arrow buttons.

The preview shows the selected page. Rotate, reorder, remove or import images.
PDF exports contain all pages in workspace order; PNG/JPEG exports contain only
the selected page. Export is atomic, with the themed Qt save dialog handling overwrite
confirmation. Ctrl+S exports, Ctrl+O imports, Escape stops scanning.

Scan pages are temporary until exported. The app warns before closing a session
with pages or an active operation. A scan interrupted by cancellation keeps complete
pages; a crash may leave temporary files under your system's temp directory.

## Print, copy and device settings

In Device, **Add printer** enables CUPS and creates a driverless IPP queue called
`Brother_MFC_L2800DW`. Polkit prompts for administrator authentication. It uses
`ipp://192.168.1.146/ipp/print` and does not change the system default printer.
Printing supports copies, A4/Letter, page ranges and duplex along the long edge.
Refresh the print queue to inspect and cancel jobs.

Use **Print scan** to copy through the computer. Direct copying and fax transmission
use the device panel. **Device settings** opens Brother's web interface for toner,
drum, network, fax and other advanced controls. Enter the administrator password in
the browser; the app never stores it. These vendor settings are not reimplemented
as native controls.

## Omarchy integration

The app reads the live palette from `~/.local/state/omarchy/current/theme/colors.toml`
and checks for changes every 1.5 seconds. Older `~/.config/omarchy/current` and
Alacritty palette files are supported. No system theme files or Omarchy sources
are modified. Tokyo Night is the fallback outside Omarchy. The Device page offers
reduced interface animations. Qt Quick runs natively on Wayland.

Preferences and the last 12 export paths live in
`$XDG_CONFIG_HOME/brother-studio/settings.json` (default `~/.config`).
The app discovers scanners by IP and prefers sane-airscan. It only lists Brother
printer queues or queues pointing at the configured IP, avoiding unrelated defaults.

## Verification

```sh
QT_QPA_PLATFORM=offscreen .venv/bin/python -m unittest discover -s tests -v
QT_QPA_PLATFORM=offscreen ./run.sh --smoke
qmllint brother_studio/ui/Main.qml
```

Smoke mode loads the actual QML and writes `/tmp/brother-studio-preview.png` without
accessing hardware. Tests cover palette paths, address matching, scan arguments,
PDF/image export, atomic failure, page operations, print options, worker threading
and rendering all four workspaces. Hardware availability depends on the network,
scanner power and installed system backends; errors appear in the status bar.

Verified on this machine: 19 checks passed; QML lint and all workspace renders
passed; the real printer at `192.168.1.146` produced an 827 × 1169 pixel flatbed
scan at 100 DPI and a PDF export. Hyprland confirmed the application window is
native Wayland (`xwayland: false`). A printer queue has not yet been created;
use **Device → Add printer** to enable printing. No print job was submitted.

To repeat the hardware check (moves the scanner and captures whatever is on the glass):

```sh
.venv/bin/python tools/verify_device.py --scan
```

The test exports to `/tmp/brother-studio-hardware-test.pdf`.

Regression checks also verify that selected DPI/source/colour settings survive
scan status updates, and all file selectors keep a consistent palette through
live dark/light theme changes. File selectors use the app's Qt Quick style and
complete Omarchy palette rather than a separately styled platform dialog.

## Licence

MIT — see [LICENSE](LICENSE). Brother Studio is an independent project and is
not affiliated with or endorsed by Brother Industries.
