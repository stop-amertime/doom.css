#!/usr/bin/env python3
"""
Generate x86CSS HTML/CSS for Doom8088.

Takes doom_x86css.com and optionally a WAD file, embeds them into the CSS
memory space, and generates the final x86css.html.

Memory layout:
  0x00000 - 0x000FF  PSP (zeroed, NOPs)
  0x00100 - ???      doom_x86css.com binary
  0x2C000 - 0x9FFF7  Heap (conventional memory)
  0x9FFF8 - 0x9FFFF  Stack
  0xB8000 - 0xB9FFF  Video memory (text mode, 4 pages)
  0xC0000 - ???      WAD file (if provided)

Usage:
  python3 build_doom_css.py [--wad DOOM16DT.WAD]
"""

import sys
import os
import argparse

# Change to upstream directory where base_template.html lives
UPSTREAM_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'x86css', 'upstream')

def main():
    parser = argparse.ArgumentParser(description='Generate Doom x86CSS')
    parser.add_argument('--binary', default=os.path.join(os.path.dirname(os.path.abspath(__file__)), 'doom_x86css.bin'),
                        help='Path to doom_x86css.bin (flat binary from exe2flat.py)')
    parser.add_argument('--wad', default=None, help='Path to DOOM16DT.WAD (optional)')
    parser.add_argument('--output', default=os.path.join(os.path.dirname(os.path.abspath(__file__)), 'doom_x86css.html'),
                        help='Output HTML file')
    parser.add_argument('--css-only', default=None, help='Also write standalone CSS file')
    args = parser.parse_args()

    # Read the binary
    with open(args.binary, 'rb') as f:
        program = f.read()
    print(f"Binary: {len(program)} bytes ({len(program)/1024:.1f} KB)")

    # Read WAD if provided
    wad_data = b''
    if args.wad:
        with open(args.wad, 'rb') as f:
            wad_data = f.read()
        print(f"WAD: {len(wad_data)} bytes ({len(wad_data)/1024:.1f} KB)")

    # Memory layout constants
    PROG_OFFSET = 0x100
    HEAP_START = 0x2C000
    STACK_TOP = 0x9FFF8
    VIDEO_BASE = 0xB8000
    VIDEO_SIZE = 0x2000  # 8KB for 4 text pages
    WAD_BASE = 0xC0000

    # Calculate total memory needed
    program_end = PROG_OFFSET + len(program)
    if wad_data:
        total_mem = WAD_BASE + len(wad_data)
    else:
        # Without WAD, just need up to video memory end
        total_mem = VIDEO_BASE + VIDEO_SIZE

    print(f"Program: 0x{PROG_OFFSET:05X} - 0x{program_end:05X}")
    print(f"Heap:    0x{HEAP_START:05X} - 0x{STACK_TOP:05X}")
    print(f"Video:   0x{VIDEO_BASE:05X} - 0x{VIDEO_BASE + VIDEO_SIZE:05X}")
    if wad_data:
        print(f"WAD:     0x{WAD_BASE:05X} - 0x{WAD_BASE + len(wad_data):05X}")
    print(f"Total:   {total_mem} bytes ({total_mem/1024:.1f} KB, {total_mem/1024/1024:.1f} MB)")
    print(f"CSS properties: ~{total_mem} (will be absorbed by calcify)")

    # Now run the upstream build_css.py logic but with our memory layout.
    # We need to be in the upstream directory for base_template.html.
    os.chdir(UPSTREAM_DIR)

    import json
    with open("x86-instructions-rebane.json", "r") as f:
        all_insts = json.load(f)

    # --- Build variables array ---
    # This mirrors build_css.py but with scaled memory.

    CPU_CYCLE_MS = 1  # Run as fast as possible for calcify

    MEM_SIZE = total_mem
    SCREEN_RAM_POS = VIDEO_BASE

    epic_charset = "XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX" + \
    ' !"#$%&\'()*+,-./0123456789:;<=>?@ABCDEFGHIJKLMNOPQRSTUVWXYZ[\\]^_`abcdefghijklmnopqrstuvwxyz{|}~' + \
    'X'*141
    epic_charset = [x for x in epic_charset]
    epic_charset[0] = ""
    epic_charset[0x0a] = "\\a "
    epic_charset[ord('"')] = "\\\""
    epic_charset[ord('\\')] = "\\\\"
    epic_charset[0x80] = "D"  # Simplified charset for Doom
    epic_charset[0x81] = "#"
    epic_charset[0x82] = "="
    epic_charset[0x83] = "+"
    epic_charset[0x84] = "."
    epic_charset[0x85] = "@"

    def createChosenMemoryInt(name, i, render, chosen):
        return [f"{name}",
                f"if(style(--addrDestA:{i}):var(--addrValA1);"
                + (f"style(--addrDestA:{i-1}) and style(--isWordWrite:1):var(--addrValA2);" if i > 0 else "")
                + f"style(--addrDestB:{i}):var(--addrValB);else:var(--__1{name}))",
                str(chosen), render]

    def createEmptyInt(name, i, render):
        return [f"{name}",
                f"if(style(--addrDestA:{i}):var(--addrValA);style(--addrDestB:{i}):var(--addrValB);else:var(--__1{name}))",
                "0", render]

    def createSplitRegister(name, i, render):
        return [f"{name}",
                f"if("
                + (f"style(--__1IP:{0x2006}):var(--keyboard, 0);" if name == "AX" else "")
                + f"style(--addrDestA:{i}):var(--addrValA);style(--addrDestB:{i}):var(--addrValB);"
                  f"style(--addrDestA:{i-20}):calc(var(--addrValA) * 256 + --lowerBytes(var(--__1{name}), 8));"
                  f"style(--addrDestB:{i-20}):calc(var(--addrValB) * 256 + --lowerBytes(var(--__1{name}), 8));"
                  f"style(--addrDestA:{i-30}):calc(round(down, var(--__1{name}) / 256) * 256 + --lowerBytes(var(--addrValA), 8));"
                  f"style(--addrDestB:{i-30}):calc(round(down, var(--__1{name}) / 256) * 256 + --lowerBytes(var(--addrValB), 8));"
                  f"else:var(--__1{name}))",
                "0", render]

    # Start building variables
    variables = [
        ["frame-count", "& + 1", "0", True],
    ]

    # Read entry and stack info from the exe2flat output
    start_file = os.path.splitext(args.binary)[0] + '.start'
    entry_offset = 0
    if os.path.exists(start_file):
        with open(start_file) as f:
            entry_offset = int(f.read().strip())
    CODE_START = PROG_OFFSET + entry_offset

    # For MZ EXE, we need to set CS and SS from the header.
    # The exe2flat.py converts to flat binary with relocations applied.
    # Default CS=0 (flat model), SS points to stack area.
    # IP is flat address, CS*16+IP should equal CODE_START.
    INIT_CS = 0x000E  # Relocated CS from exe2flat
    INIT_SS = 0x1CAF  # Relocated SS from exe2flat
    INIT_SP = 0x0000  # SP from header

    # Registers (matching upstream build_css.py with multiwrite side channels)
    variables.append(createSplitRegister("AX", -1, True))
    variables.append(createSplitRegister("CX", -2, True))
    variables.append(createSplitRegister("DX", -3, True))
    variables.append(createSplitRegister("BX", -4, True))

    # SP with --moveStack side channel.
    variables.append(["SP",
                      "if(style(--addrDestA:-5):var(--addrValA);style(--addrDestB:-5):var(--addrValB);"
                      "else:calc(var(--__1SP) + var(--moveStack)))",
                      str(INIT_SP), True])
    variables.append(createEmptyInt("BP", -6, True))

    # SI/DI with moveSI/moveDI side channels
    variables.append(["SI",
                      "if(style(--addrDestA:-7):var(--addrValA);style(--addrDestB:-7):var(--addrValB);"
                      "else:calc(var(--__1SI) + var(--moveSI)))",
                      "0", True])
    variables.append(["DI",
                      "if(style(--addrDestA:-8):var(--addrValA);style(--addrDestB:-8):var(--addrValB);"
                      "else:calc(var(--__1DI) + var(--moveDI)))",
                      "0", True])

    # IP
    variables.append(["IP",
                      "if(style(--addrDestA:-9):var(--addrValA);style(--addrDestB:-9):var(--addrValB);"
                      "style(--addrJump:-1):calc(var(--__1IP) + var(--instLen));else:var(--addrJump))",
                      str(CODE_START), True])

    # Segment registers — initialized from EXE header
    variables.append(createEmptyInt("ES", -10, True))
    variables.append(["CS",
                      "if(style(--addrDestA:-11):var(--addrValA);style(--addrDestB:-11):var(--addrValB);"
                      "else:var(--jumpCS))",
                      str(INIT_CS), True])
    variables.append(["SS",
                      "if(style(--addrDestA:-12):var(--addrValA);style(--addrDestB:-12):var(--addrValB);"
                      "else:var(--__1SS))",
                      str(INIT_SS), True])
    # DS = PSP segment (same as load_seg for COM-like behavior)
    variables.append(["DS",
                      "if(style(--addrDestA:-13):var(--addrValA);style(--addrDestB:-13):var(--addrValB);"
                      "else:var(--__1DS))",
                      "0", True])

    # Flags with --newFlags side channel
    variables.append(["flags",
                      "if(style(--addrDestA:-14):var(--addrValA);style(--addrDestB:-14):var(--addrValB);"
                      "else:var(--newFlags))",
                      "0", True])

    var_offset = len(variables)

    # --- Memory cells ---
    print(f"Generating {MEM_SIZE} memory properties...")
    for i in range(MEM_SIZE):
        # Default: NOP (0x90) below PROG_OFFSET, 0 otherwise
        default = 0x90 if i < PROG_OFFSET else 0
        variables.append(createChosenMemoryInt(f"m{i}", i, True, default))

    # Mark address 0 as INT 3 (0xCC) for debugging
    variables[0x0 + var_offset][2] = str(0xCC)

    # PSP command tail: offset 0x80 = length (0), 0x81 = CR terminator (0x0D)
    # Without this, CRT startup scans 144 bytes of NOPs as "command line arguments"
    variables[0x80 + var_offset][2] = str(0)
    variables[0x81 + var_offset][2] = str(0x0D)

    # --- Load program binary ---
    print(f"Loading binary at offset 0x{PROG_OFFSET:X}...")
    program_start = PROG_OFFSET + var_offset
    for i, b in enumerate(program):
        variables[program_start + i][2] = str(b)

    # --- Load WAD data ---
    if wad_data:
        print(f"Loading WAD at offset 0x{WAD_BASE:X}...")
        wad_start = WAD_BASE + var_offset
        for i, b in enumerate(wad_data):
            if i % 100000 == 0 and i > 0:
                print(f"  {i}/{len(wad_data)} ({100*i/len(wad_data):.0f}%)")
            variables[wad_start + i][2] = str(b)

    # --- External functions (BIOS stubs) ---
    EXTERNAL_FUNCTIONS_START = 0x2000
    EXTERNAL_FUNCTIONS_END = 0x2010
    EXTFUNS = {
        "writeChar1": [0x2000, 2],
        "writeChar4": [0x2002, 2],
        "writeChar8": [0x2004, 2],
        "readInput": [0x2006, 0],
    }

    EXTERNAL_IO_START = 0x2100
    EXTERNAL_IO_END = 0x2110

    for i in range(EXTERNAL_FUNCTIONS_START, EXTERNAL_FUNCTIONS_END):
        target_loc = var_offset + i
        if target_loc < len(variables):
            variables[target_loc][2] = str(0xc3)  # RET

    for i in range(EXTERNAL_IO_START, EXTERNAL_IO_END):
        target_loc = var_offset + i
        if target_loc < len(variables):
            variables[target_loc][2] = str(0x00)

    # --- Split into RW and RO ---
    variables_rw = variables[:program_start] + variables[program_start + len(program):]
    variables_ro = variables[program_start:program_start + len(program)]

    print(f"Variables: {len(variables)} total ({len(variables_rw)} RW, {len(variables_ro)} RO)")

    # --- Load template ---
    with open("base_template.html", "r") as f:
        HTML_TEMPL = f.read()

    for k, v in EXTFUNS.items():
        HTML_TEMPL = HTML_TEMPL.replace(f"#{k}", str(v[0]))

    # --- Generate CSS sections ---
    print("Generating CSS...")

    # @property declarations
    vars_1 = "\n".join([f"""@property --{v[0]} {{
  syntax: "<integer>";
  initial-value: {v[2]};
  inherits: true;
}}""" for v in variables])

    # Triple-buffer phase 1: read from phase 2
    vars_2a = "\n".join(
        [f"--__1{v[0]}: var(--__2{v[0]}, {v[2]});" for v in variables_rw]
        + [f"--__1{v[0]}: {v[2]};" for v in variables_ro]
    )

    # Phase 2: compute new values
    vars_2b = "\n".join([
        f"--{v[0]}: calc({v[1].replace('&', 'var(--__1' + v[0] + ')')});"
        for v in variables
    ])

    # Phase 3: write back
    vars_3 = "\n".join([f"--__2{v[0]}: var(--__0{v[0]}, {v[2]});" for v in variables_rw])
    vars_4 = "\n".join([f"--__0{v[0]}: var(--{v[0]});" for v in variables_rw])

    # Counter registration
    vars_5 = " ".join([f" {v[0]} var(--{v[0]})" for v in variables if v[3]])
    vars_6 = " ".join([f'"\\a --{v[0]}: " counter({v[0]})' for v in variables if v[3]])

    # --- readMem dispatch ---
    readmem_1 = """
style(--at:-1): var(--__1AX);
style(--at:-2): var(--__1CX);
style(--at:-3): var(--__1DX);
style(--at:-4): var(--__1BX);
style(--at:-5): var(--__1SP);
style(--at:-6): var(--__1BP);
style(--at:-7): var(--__1SI);
style(--at:-8): var(--__1DI);
style(--at:-9): var(--__1IP);
style(--at:-10):var(--__1ES);
style(--at:-11):var(--__1CS);
style(--at:-12):var(--__1SS);
style(--at:-13):var(--__1DS);
style(--at:-14):var(--__1flags);
style(--at:-21):var(--AH);
style(--at:-22):var(--CH);
style(--at:-23):var(--DH);
style(--at:-24):var(--BH);
style(--at:-31):var(--AL);
style(--at:-32):var(--CL);
style(--at:-33):var(--DL);
style(--at:-34):var(--BL);"""
    readmem_1 += ";".join(f"style(--at:{i}):var(--__1m{i})" for i in range(MEM_SIZE))
    readmem_1 += ";" + ";".join(f"style(--at:{i}):var(--__1m{i})" for i in range(EXTERNAL_FUNCTIONS_START, EXTERNAL_FUNCTIONS_END))
    readmem_1 += ";" + ";".join(f"style(--at:{i}):var(--__1m{i})" for i in range(EXTERNAL_IO_START, EXTERNAL_IO_END))

    # --- Instruction dispatch tables ---
    args_list = [
        None, "Ap", "Eb", "Ev", "Ew", "Gb", "Gv", "I0", "Ib", "Iv", "Iw",
        "Jb", "Jv", "Mp", "Ob", "Ov", "Sw",
        "AL", "CL", "DL", "BL", "AH", "CH", "DH", "BH",
        "eAX", "eCX", "eDX", "eBX", "eSP", "eBP", "eSI", "eDI",
        "ES", "CS", "SS", "DS", "1", "3", "M",
    ]

    inst_id1 = ";".join(
        f"style(--inst0:{v['opcode']})"
        + (f" and style(--modRm_reg:{v['group']})" if v['group'] is not None else "")
        + f":{v['inst_id']}"
        for v in all_insts
    )
    inst_str1 = ";".join(f"style(--instId:{v['inst_id']}):'{v['name']}'" for v in all_insts)

    inst_dest1 = ""
    inst_val1 = ""
    inst_flagfun1 = ""
    for v in all_insts:
        fun = f"--D-{v['name'].replace('.','_').replace(':','_')}"
        if fun + "(" in HTML_TEMPL:
            inst_dest1 += f"style(--instId:{v['inst_id']}):{fun}(var(--w));"
        fun = f"--V-{v['name'].replace('.','_').replace(':','_')}"
        if fun + "(" in HTML_TEMPL:
            inst_val1 += f"style(--instId:{v['inst_id']}):{fun}(var(--w));"
        fun = f"--F-{v['name'].replace('.','_').replace(':','_')}"
        if fun + "(" in HTML_TEMPL:
            inst_flagfun1 += f"style(--instId:{v['inst_id']}):{fun}(var(--baseFlags));"
    inst_dest1 = inst_dest1[:-1]
    inst_val1 = inst_val1[:-1]

    inst_len1 = ";".join(f"style(--instId:{v['inst_id']}):{v['length']}" for v in all_insts if v['length'] != 1)
    inst_modrm1 = ";".join(f"style(--instId:{v['inst_id']}):1" for v in all_insts if v['modrm'])
    inst_movestack1 = ";".join(f"style(--instId:{v['inst_id']}):{v['stack']}" for v in all_insts if v['stack'])
    inst_args1 = ";".join(f"style(--instId:{v['inst_id']}):{args_list.index(v['arg1'])}" for v in all_insts if v['arg1'])
    inst_args2 = ";".join(f"style(--instId:{v['inst_id']}):{args_list.index(v['arg2'])}" for v in all_insts if v['arg2'])
    inst_flags1 = ";".join(f"style(--instId:{v['inst_id']}):{v['flags']}" for v in all_insts if v['flags'])

    charmap1 = ";".join(f'style(--i:{i}):"{c}"' for i, c in enumerate(epic_charset))

    MAX_STRING = 5
    readstr1 = "\n".join(f'--c{i}: --readMem(calc(var(--at) + {i}));' for i in range(1, MAX_STRING))
    readstr2 = ""
    for i in range(MAX_STRING):
        fullstr = ""
        for j in range(i):
            fullstr += f'--i2char(var(--c{j})) '
        readstr2 += f"style(--c{i}:0): {fullstr};" if i < MAX_STRING - 1 else f"else:{fullstr}"

    # Simplified screen rendering for text mode
    SCREEN_WIDTH = 40
    SCREEN_HEIGHT = 25
    screen_cr = ""
    screen_cc = ""

    # Box shadow screen - simplified for text mode
    box_shadow_scrn = ""
    for x in range(SCREEN_WIDTH):
        for y in range(SCREEN_HEIGHT):
            mem_off = VIDEO_BASE + (x + y * SCREEN_WIDTH) * 2  # Text mode: char+attr pairs
            box_shadow_scrn += f"{x*8}px {y*8+8}px rgb(var(--m{mem_off}), var(--m{mem_off}), var(--m{mem_off})),"
    if box_shadow_scrn:
        box_shadow_scrn = box_shadow_scrn[:-1]

    # --- Write output ---
    print(f"Writing output to {args.output}...")
    output = HTML_TEMPL \
        .replace("CPU_CYCLE_MS", str(CPU_CYCLE_MS)) \
        .replace("READMEM_1", readmem_1) \
        .replace("INST_STR1", inst_str1) \
        .replace("INST_ID1", inst_id1) \
        .replace("INST_DEST1", inst_dest1) \
        .replace("INST_VAL1", inst_val1) \
        .replace("INST_LEN1", inst_len1) \
        .replace("INST_MODRM1", inst_modrm1) \
        .replace("INST_MOVESTACK1", inst_movestack1) \
        .replace("INST_ARGS1", inst_args1) \
        .replace("INST_ARGS2", inst_args2) \
        .replace("INST_FLAGS1", inst_flags1) \
        .replace("INST_FLAGFUN1", inst_flagfun1) \
        .replace("READSTR1", readstr1) \
        .replace("READSTR2", readstr2) \
        .replace("VARS_1", vars_1) \
        .replace("VARS_2a", vars_2a) \
        .replace("VARS_2b", vars_2b) \
        .replace("VARS_3", vars_3) \
        .replace("VARS_4", vars_4) \
        .replace("VARS_5", vars_5) \
        .replace("VARS_6", vars_6) \
        .replace("BOX_SHADOW_SCRN", box_shadow_scrn) \
        .replace("CHARMAP1", charmap1) \
        .replace("SCREEN_CR", screen_cr) \
        .replace("SCREEN_CC", screen_cc) \
        .replace("SCREEN_RAM_POS", str(SCREEN_RAM_POS))

    with open(args.output, "w", encoding="utf-8") as f:
        f.write(output)

    output_size = os.path.getsize(args.output)
    print(f"Output: {args.output} ({output_size} bytes, {output_size/1024/1024:.1f} MB)")

    # Optionally extract just the CSS
    if args.css_only:
        # Extract style blocks from HTML
        import re
        styles = re.findall(r'<style[^>]*>(.*?)</style>', output, re.DOTALL)
        css = "\n".join(styles)
        with open(args.css_only, "w", encoding="utf-8") as f:
            f.write(css)
        css_size = os.path.getsize(args.css_only)
        print(f"CSS: {args.css_only} ({css_size} bytes, {css_size/1024/1024:.1f} MB)")

    print("Done!")


if __name__ == "__main__":
    main()
