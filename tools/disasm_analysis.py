#!/usr/bin/env python3
"""
Analyze objdump disassembly output to count instruction usage
and cross-reference against x86CSS's implemented instruction set.

Usage:
    python disasm_analysis.py <disasm.txt> [--json-out report.json]

Input: output of `ia16-elf-objdump -Mi8086 -Mintel -fd <binary>`
"""

import re
import sys
import json
import os
from collections import Counter

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(SCRIPT_DIR)
BASE_TEMPLATE = os.path.join(REPO_ROOT, "x86css", "upstream", "base_template.html")
INSTRUCTIONS_JSON = os.path.join(REPO_ROOT, "x86css", "upstream", "x86-instructions-rebane.json")

# Map objdump mnemonics to x86CSS instruction names
MNEMONIC_MAP = {
    "jo": "JO", "jno": "JNO", "jb": "JB", "jnb": "JNB", "jnae": "JB",
    "jae": "JNB", "jz": "JZ", "je": "JZ", "jnz": "JNZ", "jne": "JNZ",
    "jbe": "JBE", "jna": "JBE", "ja": "JA", "jnbe": "JA",
    "js": "JS", "jns": "JNS", "jpe": "JPE", "jp": "JPE",
    "jpo": "JPO", "jnp": "JPO", "jl": "JL", "jnge": "JL",
    "jge": "JGE", "jnl": "JGE", "jle": "JLE", "jng": "JLE",
    "jg": "JG", "jnle": "JG", "jcxz": "JCXZ",
    "loop": "LOOP", "loopnz": "LOOPNZ", "loopne": "LOOPNZ",
    "loopz": "LOOPZ", "loope": "LOOPZ",
    "add": "ADD", "adc": "ADC", "sub": "SUB", "sbb": "SBB",
    "and": "AND", "or": "OR", "xor": "XOR", "cmp": "CMP",
    "test": "TEST", "mov": "MOV", "lea": "LEA",
    "push": "PUSH", "pop": "POP", "pushf": "PUSHF", "popf": "POPF",
    "inc": "INC", "dec": "DEC", "neg": "NEG", "not": "NOT",
    "mul": "MUL", "imul": "IMUL", "div": "DIV", "idiv": "IDIV",
    "shl": "SHL", "sal": "SHL", "shr": "SHR", "sar": "SAR",
    "rol": "ROL", "ror": "ROR", "rcl": "RCL", "rcr": "RCR",
    "call": "CALL", "lcall": "CALL_FAR", "ret": "RET", "retf": "RETF", "lret": "RETF",
    "jmp": "JMP", "ljmp": "JMP_FAR",
    "int": "INT", "iret": "IRET", "into": "INTO",
    "nop": "NOP", "hlt": "HLT", "wait": "WAIT",
    "cbw": "CBW", "cwd": "CWD",
    "xchg": "XCHG",
    "in": "IN", "out": "OUT",
    "movsb": "MOVSB", "movsw": "MOVSW",
    "cmpsb": "CMPSB", "cmpsw": "CMPSW",
    "scasb": "SCASB", "scasw": "SCASW",
    "lodsb": "LODSB", "lodsw": "LODSW",
    "stosb": "STOSB", "stosw": "STOSW",
    "lahf": "LAHF", "sahf": "SAHF",
    "les": "LES", "lds": "LDS",
    "clc": "CLC", "stc": "STC", "cmc": "CMC",
    "cld": "CLD", "std": "STD",
    "cli": "CLI", "sti": "STI",
    "xlat": "XLAT", "xlatb": "XLAT",
    "lock": "LOCK",
    "rep": "REPZ", "repe": "REPZ", "repz": "REPZ",
    "repne": "REPNZ", "repnz": "REPNZ",
    "aaa": "AAA", "aas": "AAS", "aam": "AAM", "aad": "AAD",
    "daa": "DAA", "das": "DAS",
}


def find_implemented():
    """Find which instructions have CSS implementations."""
    with open(BASE_TEMPLATE) as f:
        template = f.read()
    with open(INSTRUCTIONS_JSON) as f:
        all_insts = json.load(f)

    implemented = set()
    for inst in all_insts:
        name = inst["name"].replace(".", "_").replace(":", "_")
        if f"--D-{name}(" in template or f"--V-{name}(" in template:
            implemented.add(inst["name"])
    return implemented


def parse_disasm(path):
    """Parse objdump output and count instruction mnemonics."""
    counts = Counter()

    with open(path) as f:
        for line in f:
            # Match disassembly lines: "  100:  89 c3   mov    bx,ax"
            m = re.match(r'\s+[0-9a-f]+:\s+(?:[0-9a-f]{2}\s)+\s+(\S+)', line)
            if m:
                mnemonic = m.group(1).lower().rstrip("w").rstrip("b")
                # Handle segment override prefixes
                if mnemonic in ("cs", "ds", "es", "ss"):
                    continue
                # Normalize
                canonical = MNEMONIC_MAP.get(mnemonic)
                if canonical is None:
                    # Try without size suffix
                    canonical = MNEMONIC_MAP.get(mnemonic.rstrip("l").rstrip("d"))
                if canonical:
                    counts[canonical] += 1
                else:
                    counts[f"UNKNOWN:{mnemonic}"] += 1

    return counts


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Disassembly instruction gap analysis")
    parser.add_argument("disasm", help="Path to objdump disassembly output")
    parser.add_argument("--json-out", help="Write report as JSON")
    args = parser.parse_args()

    implemented = find_implemented()
    # CALL_FAR and JMP_FAR are special — CALL/JMP exist but don't handle far
    partially_implemented = {"CALL_FAR", "JMP_FAR"}

    counts = parse_disasm(args.disasm)

    print(f"=== Disassembly Analysis: {args.disasm} ===")
    print(f"Total instructions parsed: {sum(counts.values())}")
    print(f"Unique mnemonics: {len(counts)}")
    print()

    # Categorize
    ok = {}
    missing = {}
    partial = {}
    unknown = {}

    for name, count in counts.most_common():
        if name.startswith("UNKNOWN:"):
            unknown[name] = count
        elif name in partially_implemented:
            partial[name] = count
        elif name in implemented:
            ok[name] = count
        else:
            missing[name] = count

    if missing:
        print("MISSING INSTRUCTIONS (not implemented in x86CSS):")
        print(f"  {'Instruction':<15} {'Count':>8}  Priority")
        print("  " + "-" * 40)
        for name, count in sorted(missing.items(), key=lambda x: -x[1]):
            p = "CRITICAL" if count > 500 else "HIGH" if count > 100 else "MEDIUM" if count > 25 else "LOW"
            print(f"  {name:<15} {count:>8}  {p}")
        print(f"  Total missing instruction occurrences: {sum(missing.values())}")
        print()

    if partial:
        print("PARTIALLY IMPLEMENTED (exist but need extension):")
        for name, count in sorted(partial.items(), key=lambda x: -x[1]):
            print(f"  {name:<15} {count:>8}")
        print()

    if ok:
        print("IMPLEMENTED (should work):")
        for name, count in sorted(ok.items(), key=lambda x: -x[1]):
            print(f"  {name:<15} {count:>8}")
        print()

    if unknown:
        print("UNKNOWN MNEMONICS (not in mapping):")
        for name, count in sorted(unknown.items(), key=lambda x: -x[1]):
            print(f"  {name:<15} {count:>8}")
        print()

    if args.json_out:
        report = {
            "implemented": ok,
            "missing": missing,
            "partial": partial,
            "unknown": unknown,
        }
        with open(args.json_out, "w") as f:
            json.dump(report, f, indent=2)
        print(f"Report written to {args.json_out}")


if __name__ == "__main__":
    main()
