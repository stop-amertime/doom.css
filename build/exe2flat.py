#!/usr/bin/env python3
"""
Convert an MZ EXE to a flat binary image with relocations applied.

Simulates what DOS does when loading an EXE:
1. Strip the MZ header
2. Apply segment fixups at the load segment
3. Output a flat binary ready to be embedded in CSS memory at PROG_OFFSET.

Usage:
  python3 exe2flat.py doom_x86css.com doom_x86css.bin [--load-seg 0x10]
"""

import struct
import sys
import os


def main():
    if len(sys.argv) < 3:
        print(f"Usage: {sys.argv[0]} <input.exe> <output.bin> [--load-seg SEG]")
        sys.exit(1)

    input_path = sys.argv[1]
    output_path = sys.argv[2]

    # DOS loads PSP at load_seg, image at load_seg+0x10.
    # Segment references in the EXE are relative to the image start,
    # so we add (load_seg + 0x10) to relocate them.
    # For x86CSS with PSP at 0x0000 and image at 0x0100: load_seg = 0.
    load_seg = 0x0
    if '--load-seg' in sys.argv:
        idx = sys.argv.index('--load-seg')
        load_seg = int(sys.argv[idx + 1], 0)

    reloc_base = load_seg + 0x10  # Image base segment

    with open(input_path, 'rb') as f:
        data = f.read()

    # Parse MZ header
    if data[0:2] != b'MZ' and data[0:2] != b'ZM':
        print("Not an MZ EXE — copying as flat binary")
        with open(output_path, 'wb') as f:
            f.write(data)
        return

    last_page_bytes = struct.unpack_from('<H', data, 2)[0]
    pages = struct.unpack_from('<H', data, 4)[0]
    num_relocs = struct.unpack_from('<H', data, 6)[0]
    header_paragraphs = struct.unpack_from('<H', data, 8)[0]
    min_extra = struct.unpack_from('<H', data, 10)[0]
    max_extra = struct.unpack_from('<H', data, 12)[0]
    init_ss = struct.unpack_from('<H', data, 14)[0]
    init_sp = struct.unpack_from('<H', data, 16)[0]
    checksum = struct.unpack_from('<H', data, 18)[0]
    init_ip = struct.unpack_from('<H', data, 20)[0]
    init_cs = struct.unpack_from('<H', data, 22)[0]
    reloc_table_offset = struct.unpack_from('<H', data, 24)[0]

    header_size = header_paragraphs * 16

    # Calculate image size
    if last_page_bytes > 0:
        image_size = (pages - 1) * 512 + last_page_bytes - header_size
    else:
        image_size = pages * 512 - header_size

    print(f"MZ EXE: {len(data)} bytes")
    print(f"  Header: {header_size} bytes ({header_paragraphs} paragraphs)")
    print(f"  Image size: {image_size} bytes ({image_size/1024:.1f} KB)")
    print(f"  Entry: CS:IP = {init_cs:04X}:{init_ip:04X}")
    print(f"  Stack: SS:SP = {init_ss:04X}:{init_sp:04X}")
    print(f"  Relocations: {num_relocs}")
    print(f"  Load segment: 0x{load_seg:04X} (reloc base: 0x{reloc_base:04X})")

    # Extract the image (everything after header)
    image = bytearray(data[header_size:header_size + image_size])

    # Apply relocations
    # Each relocation is a seg:off pair pointing to a word in the image
    # that needs the load segment added to it.
    relocs_applied = 0
    for i in range(num_relocs):
        reloc_offset = reloc_table_offset + i * 4
        off = struct.unpack_from('<H', data, reloc_offset)[0]
        seg = struct.unpack_from('<H', data, reloc_offset + 2)[0]

        # Calculate position in image
        pos = seg * 16 + off
        if pos + 1 < len(image):
            # Read the word, add relocation base, write back
            word = struct.unpack_from('<H', image, pos)[0]
            word = (word + reloc_base) & 0xFFFF
            struct.pack_into('<H', image, pos, word)
            relocs_applied += 1

    print(f"  Applied {relocs_applied} relocations")

    # Calculate entry point offset within the image
    # CS is relative to image start, so entry = (init_cs * 16) + init_ip
    # But we need to handle wrap-around for negative CS values like 0xFFFE
    adj_cs = (init_cs + reloc_base) & 0xFFFF
    entry_flat = adj_cs * 16 + init_ip
    entry_in_image = entry_flat - reloc_base * 16  # Relative to image start
    print(f"  Relocated CS:IP = {adj_cs:04X}:{init_ip:04X}")
    print(f"  Entry flat address: 0x{entry_flat:X}")
    print(f"  Entry in image: 0x{entry_in_image:X}")

    # Write the flat binary
    with open(output_path, 'wb') as f:
        f.write(image)

    # Write the entry offset (in image) to a .start file
    # This is what build_css.py reads to set IP initial value
    start_path = os.path.splitext(output_path)[0] + '.start'
    with open(start_path, 'w') as f:
        f.write(str(entry_in_image))

    # Also write SS:SP info
    adj_ss = (init_ss + reloc_base) & 0xFFFF
    stack_flat = adj_ss * 16 + init_sp
    print(f"  Relocated SS:SP = {adj_ss:04X}:{init_sp:04X} (flat: 0x{stack_flat:X})")

    print(f"Output: {output_path} ({len(image)} bytes)")
    print(f"Entry: {start_path} ({entry_in_image})")


if __name__ == '__main__':
    main()
