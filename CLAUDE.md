# doom.css

Doom8088 (8086 port of DOOM) files, mainly, plus some other files kicking around. Includes other repos. 

Besides this repo should be other repos - calcite and css-dos, which contain most of the actual work. 

USER: I think this docs is pretty out of date honestly. 

## Project Layout

```
doom8088/
  src/              Doom8088 upstream (git submodule: FrenkelS/Doom8088)

x86css/
  upstream/         x86CSS upstream (git submodule: rebane2001/x86CSS)

build/
  Dockerfile        gcc-ia16 build environment
  build.sh          Docker-wrapped build script

tools/
  instruction_gap.py    Analyze which instructions are implemented in x86CSS
  disasm_analysis.py    Analyze compiled binary for instruction usage
```

## Dependencies

- Docker — for gcc-ia16 build environment (or native gcc-ia16)
- Python 3 — for build_css.py and tools
- calc(ite) — the compute engine (sister repo, required to actually run it)
- DOOM1.WAD — shareware Doom WAD (not included, user-supplied)
- jWadUtil — converts DOOM1.WAD to DOOM16DT.WAD for text mode

## Key Numbers

- **Memory:** ~560KB conventional = ~573,000 custom properties
- **WAD:** DOOM16DT.WAD = 1,357,504 bytes (~1.3MB), loaded via DOS I/O interception
- **Display:** Text mode 40x25, video memory at 0xB800:0000, 2,000 bytes
- **Missing instructions:** 17 unimplemented + far CALL/JMP extensions
- **Binary:** 164KB compiled (C_ONLY, -Os, no LTO)
- **Generated CSS:** ~100-150MB estimated

## Missing x86 Instructions (verified from compiled binary)

Compiled with `-DC_ONLY -march=i8088 -mcmodel=medium`, 40x25 text mode.
Binary: 164KB, 58,643 instructions. Counts from actual disassembly.

### Critical — far call/return/jump (1,910 occurrences)
- Far CALL — 1,271 (1,223 direct 0x9A + 48 indirect FF/3) — must push CS:IP
- RETF — 560 — far return, pop IP and CS
- Far JMP — 79 (69 direct 0xEA + 10 indirect FF/5) — must load CS:IP

### High (569 occurrences)
- LES — 189 — load far pointer into ES:reg
- SAR — 146 — arithmetic right shift
- LOOPNZ — 132 — dec CX, jump if CX!=0 and ZF=0
- LDS — 120 — load far pointer into DS:reg

### Medium (~1,050 occurrences)
- OUT — 128, IN — 114 — port I/O (stub for most ports)
- CLC — 88 — clear carry flag
- JO — 80, JNO — 31 — jump on overflow
- RCR — 78, RCL — 71 — rotate through carry
- DAA — 69, DAS — 34 — decimal adjust (stub if unused)
- JPE — 59, JPO — 34 — jump on parity
- NEG — 51 — two's complement negate
- XLAT — 49 — table lookup AL = [BX+AL]
- CLD — 47, STD — 36 — direction flag
- JCXZ — 47 — jump if CX zero
- REPZ — 44, REPNZ — 35 — string repeat prefixes
- ROR — 41, ROL — 38 — rotate
- LOCK — 41 — bus lock prefix (stub)
- LOOP — 31, LOOPZ — 31 — loop
- CMC — 31 — complement carry
- CLI — 31, STI — 30 — interrupt flag (stub)
- LAHF — 31 — load flags into AH
- STC — 31 — set carry flag

### Low (~130 occurrences)
- HLT — 29, AAD — 30, AAA — 27, AAM — 26, AAS — 18 — mostly unreachable
- PUSHF — 25, POPF — 19
- INTO — 24, SAHF — 18
- IRET — 16

## BIOS/DOS Stubs

- `int 10h` — BIOS video: stub (mode set at startup only)
- `int 16h` — BIOS keyboard: map to x86CSS keyboard I/O address
- `int 21h` — DOS file I/O: intercept fopen/fread, serve WAD from engine buffer

## Build

```sh
# 0. Build the Docker image (once)
docker build -t doom-css-build build/

# 1. Compile Doom8088 for x86CSS (40x25 text mode, 8088 target)
cd build && ./build.sh 40 25 i8088

# 2. Analyze instruction gaps
python tools/disasm_analysis.py build/doom_disasm.txt

# 3. Generate CSS (after implementing missing instructions)
# cd build && python build_css.py ...  (TBD — pipeline needs extension)

# 4. Run via calcify (native)
cd ../calcify && cargo run --release -- ../doom.css/web/doom-x86css.html
```

## Key Finding: -DC_ONLY

All 10 ASM files in Doom8088 have C fallback implementations behind `#if defined C_ONLY`.
The Watcom build (makefile.w16) already uses `-DC_ONLY` and links zero ASM.
This means we compile with `-DC_ONLY` and skip ASM entirely.

## Development Phases

1. Compile Doom8088 with `-DC_ONLY`, text mode 40x25
2. Stub BIOS/DOS calls for x86CSS environment
3. Implement missing x86 instructions (see priority list above)
4. Extend build_css.py for ~640KB memory + 32KB video RAM at 0xB8000
5. Generate CSS, run through calcify, verify Doom boots to title screen
