# Doom8088 + x86CSS Analysis Report

Generated 2026-04-06. Mechanical analysis of upstream sources.

## x86CSS Instruction Coverage

42 of 100 instruction names implemented (have D-/V- CSS functions).

### Implemented (42)
ADC, ADD, AND, CALL, CBW, CMP, CWD, DEC, DIV, IDIV, IMUL, INC, INT, JA,
JB, JBE, JG, JGE, JL, JLE, JMP, JNB, JNS, JNZ, JS, JZ, LEA, MOV, MUL,
NOP, NOT, OR, POP, PUSH, RET, SBB, SHL, SHR, SUB, TEST, XCHG, XOR

### Partially implemented (per author's compat table)
- ADC: ignores carry flag (CF), effectively same as ADD
- SBB: ignores carry flag, effectively same as SUB
- IMUL: signed conversion may have precision issues
- IDIV: signed conversion may have precision issues
- CALL: far variants (0x9a, FF/3) treated as near — CS ignored
- JMP: far variants (0xea, FF/5) treated as near — CS ignored
- INT: only INT 3 (breakpoint) implemented
- TEST: buggy — last CSS `result:` overrides, returns arg1 not AND(arg1,arg2)

### Not implemented (58)
AAA, AAD, AAM, AAS, CLC, CLD, CLI, CMC, CMPSB, CMPSW, CS:, DAA, DAS,
DS:, ES:, HLT, IN, INTO, IRET, JCXZ, JNO, JO, JPE, JPO, LAHF, LDS, LES,
LOCK, LODSB, LODSW, LOOP, LOOPNZ, LOOPZ, MOVSB, MOVSW, NEG, OUT, POPF,
PUSHF, RCL, RCR, REPNZ, REPZ, RETF, ROL, ROR, SAHF, SAR, SCASB, SCASW,
SS:, STC, STD, STI, STOSB, STOSW, WAIT, XLAT

## Doom8088 ASM Files

All 10 ASM files have C_ONLY fallbacks. Compile with `-DC_ONLY` to use
pure C — validated by Watcom makefile.w16.

| ASM file | Functions | C_ONLY fallback |
|---|---|---|
| m_fixed.asm | FixedMul, FixedMul3232, FixedReciprocal* | m_fixed.h macros + r_draw.c |
| z_xms.asm | Z_Allocate/Free/MoveExtendedMemoryBlock | z_zone.c no-op stubs |
| i_vtexta.asm | R_DrawColumn2, R_DrawColumnFlat2 | i_vtext.c inline C |

## Doom8088 BIOS/DOS/Port I/O Surface

### Interrupts used
- INT 10h: Video mode set, cursor, palette (i_system.c, i_vtext.c)
- INT 16h: (not directly called — keyboard via ISR hook on INT 9)
- INT 21h: (not directly called — file I/O via C runtime fopen/fread)
- INT 67h: EMS memory (z_zone.c) — can be stubbed
- INT 2Fh: XMS memory (z_zone.c) — can be stubbed
- INT 8: Timer ISR hook (a_taskmn.c)
- INT 9: Keyboard ISR hook (i_system.c)

### Port I/O (text mode relevant)
- 0x3D4/0x3D5: CRTC registers (start address / page flip)
- 0x3D8: CGA mode control
- 0x3D9: CGA color select / palette
- 0x60/0x61: Keyboard controller
- 0x40/0x43: PIT timer
- 0x20: PIC EOI

### WAD loading
Pure C standard library: fopen, fread, fseek, ftell. No direct DOS calls.
XMS used as cache if available; falls back to direct file reads.
