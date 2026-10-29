# Validation status

## Software

- Direct plugin v0.4.0: 14 simulated-device tests, including endpoint filtering, 83 unique positions/names, identity/RAM1 gating, 64/65-byte feature reply handling, exact RGB ordering, checksums, fixed 5 FPS, sequence wrap, release, and stopping on bad ACK.
- Python suite: 18 updater simulated-device tests, 6 UI/defaults/confirmation tests and 2 base-image helper tests (26 total). No real flash operation occurs in those tests.
- Integrated firmware emulator report: 134 packets through the original dispatcher, 1598 LED differential cases, 16 representative legacy commands and 16 frames. Flash remained read-only in those executed paths. This does not exhaust the application or measure physical flash activity.
- Original boot parser simulation accepted both original and patched application transfers. Electrical programming was replaced by virtual memory operations.

The firmware emulator uses Unicorn. Its report documents an instrumentation issue with memory-write callbacks on baseline Thumb conditional stores; alternative instruction tracing/memory comparisons were used. There is no independent second CPU backend qualification.

## Owner observations on one unit, 2026-10-29

- Modified firmware installed through the prepared manual updater; bootloader checksum and application return were reported by the app.
- Keyboard typing reported normal.
- Esc red, A green, W blue and automatic release after three seconds reported correct.
- Continuous SignalRGB effects through the bridge reported correct.
- The direct USB plugin loaded in SignalRGB; the submitted layout screenshot shows the detected device. It does not independently prove full color behavior or long-term operation.

## Still unverified

Every key's physical mapping, peak stack under full workloads, interrupt/DMA timing, long-term stability, suspend/resume, simultaneous Akko-app access and forced recovery after an application hang. Historical JSON reports may say `hardware_tests: 0`: those describe the emulator run before the later owner observations, not a full hardware qualification.

## Reproduce

Plugin (Node.js, no dependencies): `node tests/test_plugin.cjs plugin/Akko_TAC75_HE.js`.

Firmware: obtain the exact base via `tools/prepare_base.py`, install pinned development requirements, run the builder, then the two emulator scripts. Run updater/UI tests using `python -m unittest discover -s tests -p "test_*.py"`. UI tests need a desktop/Tk environment; they do not send USB traffic.
