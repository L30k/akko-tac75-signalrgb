"""Identity/report parsing helpers. Importing this file does not access hardware."""
from __future__ import annotations
DEVICE_ID=2782
ORIGINAL_SHA256="2e188151b6025aac685855c6088959fa3d9c9058d9055bfb07a92c380b68f306"

class ValidationError(Exception):
    pass


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def packet(command: int, data: bytes = b"", checksum: bool = True) -> bytes:
    if not 0 <= command <= 255 or len(data) > 63:
        raise ValidationError("Invalid packet.")
    p = bytearray(64)
    p[0] = command
    p[1:1 + len(data)] = data
    if checksum:
        p[7] = 255 - (sum(p[:7]) & 255)
    return bytes(p)


def parse_identity(raw: bytes) -> dict:
    if len(raw) == 65 and raw[0] == 0:
        raw = raw[1:]
    if len(raw) != 64 or raw[0] != 0x8F:
        raise ValidationError("Invalid identity reply; no firmware update started.")
    device_id = int.from_bytes(raw[1:5], "little")
    if device_id != DEVICE_ID:
        raise ValidationError(f"Device replied ID{device_id}; expected ID2782.")
    return {
        "device_id": device_id,
        "firmware": f"V{raw[8]:x}{raw[7]:02x}",
        "light_sync": raw[11] == 1,
        "raw_identity": raw.hex(),
    }


def feature_layout(descriptor: bytes) -> tuple[int, int]:
    """Parse short HID items; reject ambiguous/multiple Feature reports."""
    size = count = report_id = 0
    layouts = {}
    stack = []
    pos = 0
    while pos < len(descriptor):
        lead = descriptor[pos]
        pos += 1
        if lead == 0xFE:
            if pos + 2 > len(descriptor):
                raise ValidationError("Truncated HID descriptor.")
            length = descriptor[pos]
            pos += 2 + length
            if pos > len(descriptor):
                raise ValidationError("Truncated HID descriptor.")
            continue
        length = (0, 1, 2, 4)[lead & 3]
        if pos + length > len(descriptor):
            raise ValidationError("Truncated HID descriptor.")
        value = int.from_bytes(descriptor[pos:pos + length], "little")
        pos += length
        kind, tag = (lead >> 2) & 3, lead >> 4
        if kind == 1:
            if tag == 7:
                size = value
            elif tag == 8:
                report_id = value
            elif tag == 9:
                count = value
            elif tag == 10:
                stack.append((size, count, report_id))
            elif tag == 11:
                if not stack:
                    raise ValidationError("Invalid HID descriptor stack.")
                size, count, report_id = stack.pop()
        elif kind == 0 and tag == 11:
            layouts[report_id] = layouts.get(report_id, 0) + size * count
    if layouts != {0: 512}:
        raise ValidationError(f"Unexpected feature report: {layouts}. Expected ID0 / 64 bytes.")
    return 0, 64


