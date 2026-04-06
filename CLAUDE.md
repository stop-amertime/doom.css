# doom.css

Doom running in pure CSS, powered by calc(ify). Compiles Doom8088 (a 16-bit
Doom port) to 8086 machine code, embeds it in CSS via x86CSS's build pipeline,
and runs it through the calc(ify) compute engine at playable speed.

Sister project to [calcify](../calcify/) — they share a spec
(`css-compute-engine-spec-v2-1.md`). calcify is the engine, doom.css is the demo.

## Project Layout

```
doom8088/
  src/          Doom8088 fork — C source modified for x86CSS compatibility
  build/        Compiled binaries (gcc-ia16 output)

x86css/
  instructions/ Extended instruction definitions (17 new + far CALL/JMP)
  templates/    Modified base_template.html for Doom-scale memory

build/          Build pipeline — extended build_css.py, WAD processing

web/            Browser frontend — doom-x86css.html, display renderer

tools/          Utilities — disassembler, instruction gap analysis, WAD tools
```

## Dependencies

- `gcc-ia16` — 16-bit x86 C compiler (same toolchain as x86CSS)
- Python 3 — for build_css.py and tools
- calc(ify) — the compute engine (sister repo, required to actually run it)
- DOOM1.WAD — shareware Doom WAD (not included, user-supplied)
- jWadUtil — converts DOOM1.WAD to DOOM16DT.WAD for text mode

## Key Numbers

- **Memory:** ~560KB conventional = ~573,000 custom properties
- **WAD:** DOOM16DT.WAD = 1,357,504 bytes (~1.3MB), loaded via DOS I/O interception
- **Display:** Text mode 40x25, video memory at 0xB800:0000, 2,000 bytes
- **Missing instructions:** 17 unimplemented + far CALL/JMP extensions
- **Generated CSS:** ~100-150MB estimated

## Missing x86 Instructions (by priority)

### Critical (1,565 occurrences)
- Far CALL (lcall) — 1,195 — extend existing CALL to push CS:IP
- RETF — 370 — far return, pop IP and CS
- Far JMP (ljmp) — 72 — extend existing JMP for far jumps

### High (417 occurrences)
- SAR — 123 — arithmetic right shift
- RCL — 117 — rotate left through carry
- LES — 111 — load far pointer into ES:reg
- LDS — 106 — load far pointer into DS:reg

### Medium (252 occurrences)
- NEG — 77 — two's complement negate
- CLC — 65 — clear carry flag
- RCR — 58 — rotate right through carry
- XLAT — 52 — table lookup AL = [BX+AL]

### Low (63 occurrences)
- STOSB — 25 — store byte AL to [ES:DI], inc DI
- LAHF — 16 — load flags into AH
- STI/CLI — 12 — stub (no hardware interrupts)
- IRET — 2 — return from interrupt
- PUSHF/POPF — 2 — push/pop flags register
- JCXZ — 1 — jump if CX is zero

### Port I/O
- IN — 6 — read from port
- OUT — 18 — write to port
- Ports: 0x3D4/0x3D5 (CRT registers), 0x3D9 (CGA palette), timer

## BIOS/DOS Stubs

- `int 10h` — BIOS video: stub (mode set at startup only)
- `int 16h` — BIOS keyboard: map to x86CSS keyboard I/O address
- `int 21h` — DOS file I/O: intercept fopen/fread, serve WAD from engine buffer

## Build

```sh
# 1. Compile Doom8088 for x86CSS
cd doom8088 && make

# 2. Generate CSS
cd ../build && python build_css.py ../doom8088/build/doom.com -o ../web/doom-x86css.html

# 3. Run via calcify (native)
cd ../../calcify && cargo run --release -- ../doom.css/web/doom-x86css.html
```

## Development Phases

1. Fork Doom8088, configure text mode 40x25, strip sound/EMS/XMS
2. Replace BIOS/DOS calls with x86CSS I/O conventions
3. Remove hand-written ASM (m_fixed.asm, i_vtexta.asm, z_xms.asm), use C
4. Compile with `gcc-ia16 -march=i8088 -mcmodel=medium`
5. Implement missing instructions in x86CSS
6. Extend build_css.py for ~640KB memory + 32KB video RAM at 0xB8000
7. Generate CSS, run through calcify, verify Doom boots to title screen
