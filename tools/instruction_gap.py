#!/usr/bin/env python3
"""
Instruction gap analysis tool for doom.css.

Compares x86CSS's implemented instruction set against a compiled binary
to identify which instructions need to be added.

Usage:
    python instruction_gap.py <binary.com> [--json-out report.json]
    python instruction_gap.py --template-only   # just analyze base_template.html

Requires: x86-instructions-rebane.json and base_template.html in expected paths.
"""

import json
import sys
import os
from collections import Counter

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(SCRIPT_DIR)

INSTRUCTIONS_JSON = os.path.join(REPO_ROOT, "x86css", "upstream", "x86-instructions-rebane.json")
BASE_TEMPLATE = os.path.join(REPO_ROOT, "x86css", "upstream", "base_template.html")


def load_instruction_set():
    """Load the full x86 instruction set from Rebane's JSON."""
    with open(INSTRUCTIONS_JSON) as f:
        return json.load(f)


def find_implemented_instructions(template_path):
    """Scan base_template.html for --D-xxx and --V-xxx function definitions."""
    with open(template_path) as f:
        template = f.read()

    implemented = set()
    # The build script checks for `--D-{name}(` and `--V-{name}(` in the template
    for inst in load_instruction_set():
        name = inst["name"].replace(".", "_").replace(":", "_")
        d_func = f"--D-{name}("
        v_func = f"--V-{name}("
        if d_func in template or v_func in template:
            implemented.add(inst["name"])

    return implemented


def decode_binary(binary_path, instruction_set):
    """
    Simple opcode frequency counter for a COM binary.
    Maps each byte to its instruction name(s) via the JSON.
    Does NOT do full disassembly — just first-pass opcode counting.

    For accurate results, use objdump/ndisasm on the binary.
    This gives a rough idea of instruction usage.
    """
    opcode_map = {}
    for inst in instruction_set:
        opcode = inst["opcode"]
        if opcode not in opcode_map:
            opcode_map[opcode] = []
        opcode_map[opcode].append(inst)

    with open(binary_path, "rb") as f:
        binary = f.read()

    # Simple scan: count opcode bytes (imprecise but useful for gap detection)
    opcode_counts = Counter()
    for byte in binary:
        if byte in opcode_map:
            for inst in opcode_map[byte]:
                opcode_counts[inst["name"]] += 1

    return opcode_counts


def main():
    import argparse
    parser = argparse.ArgumentParser(description="x86CSS instruction gap analysis")
    parser.add_argument("binary", nargs="?", help="Path to compiled binary (.com)")
    parser.add_argument("--template-only", action="store_true",
                        help="Only analyze which instructions are implemented in base_template.html")
    parser.add_argument("--json-out", help="Write report as JSON")
    args = parser.parse_args()

    instruction_set = load_instruction_set()
    all_names = sorted(set(i["name"] for i in instruction_set))
    implemented = find_implemented_instructions(BASE_TEMPLATE)
    not_implemented = sorted(set(all_names) - implemented)

    print(f"=== x86CSS Instruction Coverage ===")
    print(f"Total instruction names in JSON: {len(all_names)}")
    print(f"Implemented (have D-/V- functions): {len(implemented)}")
    print(f"Not implemented: {len(not_implemented)}")
    print()

    print("Implemented instructions:")
    for name in sorted(implemented):
        opcodes = [hex(i["opcode"]) for i in instruction_set if i["name"] == name]
        print(f"  {name:12s}  ({len(opcodes)} opcodes)")
    print()

    print("NOT implemented (no D-/V- function in template):")
    for name in not_implemented:
        opcodes = [hex(i["opcode"]) for i in instruction_set if i["name"] == name]
        print(f"  {name:12s}  ({len(opcodes)} opcodes)")
    print()

    if args.binary:
        print(f"=== Binary Analysis: {args.binary} ===")
        opcode_counts = decode_binary(args.binary, instruction_set)

        # Instructions used in binary but not implemented
        gaps = {}
        for name, count in opcode_counts.most_common():
            if name not in implemented:
                gaps[name] = count

        if gaps:
            print(f"\nMISSING INSTRUCTIONS (used in binary, not in x86CSS):")
            print(f"{'Instruction':<12} {'Approx Count':>12}  Priority")
            print("-" * 45)
            for name, count in sorted(gaps.items(), key=lambda x: -x[1]):
                priority = "CRITICAL" if count > 500 else "HIGH" if count > 100 else "MEDIUM" if count > 25 else "LOW"
                print(f"  {name:<12} {count:>10}    {priority}")
        else:
            print("All instructions used in the binary are implemented!")

    if args.json_out:
        report = {
            "all_instructions": all_names,
            "implemented": sorted(implemented),
            "not_implemented": not_implemented,
        }
        if args.binary:
            report["binary_gaps"] = gaps
        with open(args.json_out, "w") as f:
            json.dump(report, f, indent=2)
        print(f"\nReport written to {args.json_out}")


if __name__ == "__main__":
    main()
