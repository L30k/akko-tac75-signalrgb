# Changelog

## 0.4.0-rc.1 — Experimental prerelease, 2026-10-29

### Plugin
- Direct HID communication with the existing V502 RAM1 firmware; no bridge app required.
- Fixed 5 FPS, manual activation, identity and capability checks, per-packet ACKs and release on normal shutdown.
- Akko TAC75 HE device name, L30k attribution, 83 canonical key names and explicit LED registration.
- English controls and errors; external Akko product photo and standalone LED-index diagram.

### Firmware Manager
- New English dark interface with device/firmware/capability cards, preview and explicit install/restore actions.
- Removed the obsolete bridge server from this release's manager.
- Incorrect typed confirmation now shows a clear message without starting an update.
- Shareable plan export omits device-specific USB paths and raw identity bytes.
- Local update records remain private and are excluded from source archives.

### Firmware
- **No change to the installed V502 RAM1 image.** App/plugin version 0.4.0 is separate from firmware base V502 and RAM protocol revision 1.
- Exact patched SHA256: `b17a120cdd266c67dbc529e6972a6c452ad29923487d1c96a2700d05d9b0d753`.
- Receiver uses double-buffered RAM; stock bootloader preserved; 544 bytes reserved from the previous stack/heap arrangement.

### Repository
- Separate plugin, app, firmware patch tools, metadata, tests, assets and documentation.
- English README, Portuguese guide, protocol, architecture, recovery and validation notes.
- Original-code MIT license; third-party firmware and trademarks excluded.
- Vendor binaries are obtained locally with exact hash validation, rather than included in the public source archive.
