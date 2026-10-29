# Publication checklist — v0.4.0-rc.1 experimental

Owner: L30k. Repository name: `akko-tac75-signalrgb`. Visibility must remain **private** until the owner explicitly requests a public release.

- [x] English plugin controls/logs and main documentation; Portuguese installation guide.
- [x] Device name Akko TAC75 HE; publisher L30k; all 83 LED names assigned.
- [x] Original project code license and third-party notices.
- [x] No serial numbers, host USB location paths, private logs, screenshots, device state or credentials in the source archive.
- [x] Vendor binaries and generated executables excluded from the publication archive.
- [x] Exact firmware base hash pinned; reproducible local builder and emulator sources included.
- [x] 14 simulated plugin tests and 26 Python tests passed during preparation.
- [x] English manager UI visually checked; preview completed without opening USB.
- [x] English/Portuguese experimental-use and liability notices; prerelease version.
- [x] Local rebuild matches the previous experimental firmware SHA256.
- [ ] Owner checks renamed device, individual LED selection and lighting after restarting SignalRGB.
- [ ] Long-term stability, suspend/resume and all key positions tested.
- [ ] Recovery from a failed application demonstrated on this PCB.

Keep this as a private experimental prerelease during review. Do not describe it as generally safe or guaranteed recoverable. Review the archive, licensing choice and documentation before any future public release.

The firmware manager has an English interface and remains a developer tool. The plugin itself requires no updater process during use.
