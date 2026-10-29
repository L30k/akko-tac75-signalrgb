# What was changed

## Why a firmware patch?

The analyzed stock V502 paths for global lighting (07) and custom per-key patterns (0C) set persistence flags and can lead to configuration flash writes. Repeatedly sending animation frames through a persistent configuration path was not the desired design. This work adds a separate RAM-only receiver rather than using those stock commands for streaming.

## Data flow

```text
SignalRGB canvas
    -> plugin/Akko_TAC75_HE.js (83 RGB colors, fixed 5 FPS)
    -> HID Feature reports (identity/capability gated)
    -> added V502 RAM1 receiver
    -> inactive RGB buffer -> COMMIT -> active RGB buffer
    -> existing LED encoder/output path
```

The firmware manager is used for manual firmware installation/restoration and a short lighting check. It is absent from the runtime path above.

## Binary changes

The patch starts from one exact official ID2782 V502 image. Thirteen existing bytes change across three heap/stack limit words, a six-byte LED entry hook and a two-byte command dispatch table entry. Added code begins at 08022000, below the analyzed configuration region. The prefix through 00004FFF is identical to the official image. The ordinary USB transfer sends application bytes from offset 5000 onward, never that prefix.

The reserved context is 544 bytes at 20009D98–20009FB7, containing state and two RGB buffers. Heap capacity stays 512 bytes; stack reservation decreases from 16384 to 15840 bytes. The original startup initializer was exercised in the emulator to check context initialization and overlap. This is not a worst-case runtime stack measurement.

The 0F/A7 command selects DATA, COMMIT, RELEASE or CAPABILITIES. DATA fills the inactive buffer, COMMIT validates sequence/full-block mask and changes the active index, and RELEASE clears external control. The LED hook takes a short interrupt-masked RGB snapshot and reuses the original encoder. Existing effects remain the fallback while external control is inactive.

## Preserved versus unverified

The implementation preserves the existing command routes and bootloader bytes. Representative legacy paths were compared in emulation. The owner reported basic typing and lighting working. This is not proof that every macro, actuation, rapid-trigger, calibration, interrupt load or power-management path is unchanged. Recovery after a hang and long-term stability remain open checks.

The patch has no firmware watchdog that automatically returns lighting on host loss. A clean plugin shutdown releases control; abrupt process termination can leave the last frame until another release or keyboard restart.

## Repository structure

```text
plugin/          SignalRGB plugin (JavaScript)
app/             English firmware manager and verified USB transport
firmware_tools/  Reproducible patch builder and assembly sources
firmware/        Base-image metadata and generated local files
tests/           Simulated plugin, updater, UI and firmware tests
tools/           Obtain base firmware and build Windows manager
assets/          Schematic 83-key diagram and index map
docs/            Installation, protocol, architecture, recovery and test limits
release/         Experimental release notes
```
