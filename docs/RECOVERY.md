# Recovery limits

The updater can attempt a stock V502 restore while the application responds, or directly from a reachable vendor bootloader on the recorded USB location. Its framing was tested against the original parser in emulation. USB recovery on a failed application has **not** been demonstrated on the tested TAC75 unit.

The known-good vendor image is not a full readback of calibration/configuration from an individual keyboard. No full hardware backup was obtained. Bootloader bytes are preserved in the patch and omitted from ordinary HID transfer; this does not guarantee entry after an application hang.

Physical examination found an RY5088-marked U5 and a five-contact J2. Only the contact opposite the square pad was measured as ground. **The other J2 contacts are unverified. Do not copy a pinout from another board.** No programmer was connected and flash protections were not read.

Other RY5088 projects document USB bootloader, chip boot and SWD recovery on related boards. These are references, not validated wiring or instructions for this PCB. Unlocking protection may erase all flash; some protection levels are permanent.

- [Akko downloads and revision-specific driver guidance](https://en.akkogear.com/download/)
- [Related-platform hardware research](https://github.com/echtzeit-solutions/monsgeek-akko-linux/blob/master/docs/HARDWARE.md)
- [Related-platform flasher](https://github.com/dot-agi/ry5088-flasher)
- [AT32 access protection](https://kb.segger.com/ArteryTek_AT32)

For a recovery procedure specific to the device, contact Akko with model K0028, ID2782, firmware V502 and your revision/serial information privately. A `ry_upgrade` tool was mentioned in owner reports, but no public official TAC75-specific recovery download was verified.
