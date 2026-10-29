# RAM lighting protocol v1

USB HID Feature report ID 0, 64 payload bytes (65 bytes in SignalRGB including the report-ID prefix). The plugin accepts only interface 2, usage page FFFF, usage 2 on VID3151/PID502D.

Before colors: request identity command 8F and check little-endian ID2782 and V502; then request RAM1 capabilities with command 0F, tag A7, protocol 1, operation 4. Require bytes 8–15 `AK75RAM1`, byte16=83, byte17=1, and LE16 at18=544. USB IDs alone do not identify the firmware.

| Payload offset | Meaning |
| --- | --- |
| 0 | 0F |
| 1 | A7 |
| 2 | 01 |
| 3 | Operation: 1 DATA, 2 COMMIT, 3 RELEASE, 4 CAPABILITIES |
| 4 | Sequence (wraps at 256) |
| 5 | Block index |
| 6 | Data length |
| 7 | Header checksum: first eight bytes sum to FF modulo 256 |
| 8–63 | RGB data for DATA |

One frame contains 249 RGB bytes, in physical LED index order 0–82. Send five DATA packets with lengths 56,56,56,56,25, then COMMIT with the same sequence. DATA fills the inactive buffer; COMMIT requires the full block mask and flips the visible buffer. Check ACK payload byte8=A5, byte9=1 for DATA, 2 for COMMIT, 3 for RELEASE. Stop on an invalid reply. RELEASE clears external control and returns to the existing lighting path.

The plugin never sends stock lighting commands 07/0C, boot command 7F, boot transfer commands or configuration-save operations. This protocol does not add an autonomous timeout to the firmware. The receiver reserves 544 RAM bytes; firmware stack reservation is reduced by that amount.
