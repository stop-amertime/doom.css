#!/bin/bash
# Build Doom8088 for x86CSS using the doom-css-build Docker image.
#
# Usage:
#   ./build.sh                  # build with default settings (40x25, i8088)
#   ./build.sh 80 50 i286       # custom resolution and CPU
#
# Prerequisites:
#   docker build -t doom-css-build .

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"

WIDTH="${1:-40}"
HEIGHT="${2:-25}"
CPU="${3:-i8088}"
OUTPUT="doom.com"

echo "Building Doom8088: ${WIDTH}x${HEIGHT}, CPU=${CPU}"

docker run --rm \
  -v "${REPO_ROOT}/doom8088/src:/build/src" \
  -v "${SCRIPT_DIR}:/build/output" \
  -w /build/src \
  doom-css-build \
  bash -c "
    # Assemble ASM files
    nasm i_vtexta.asm -f elf -DCPU=${CPU} -DPLANEWIDTH=$((2*WIDTH)) -DVIEWWINDOWHEIGHT=${HEIGHT}
    nasm m_fixed.asm  -f elf -DCPU=${CPU}
    nasm z_xms.asm    -f elf -DCPU=${CPU}

    # Compile performance-critical C files separately
    RENDER_OPTIONS=\"-DFLAT_SPAN -DFLAT_NUKAGE1_COLOR=32 -DFLAT_SKY_COLOR=7 -DWAD_FILE=\\\"DOOM16DT.WAD\\\" -DVIEWWINDOWWIDTH=${WIDTH} -DVIEWWINDOWHEIGHT=${HEIGHT} -DMAPWIDTH=${WIDTH} -DNR_OF_COLORS=16\"
    CC_FLAGS=\"-march=${CPU} -mcmodel=medium -mnewlib-nano-stdio -Ofast -fomit-frame-pointer -fgcse-sm -fgcse-las -fipa-pta -mregparmcall -flto -fwhole-program -funroll-all-loops -fira-loop-pressure -freorder-blocks-algorithm=simple -fno-tree-pre\"

    for f in i_vtext.c p_enemy2.c p_map.c p_maputl.c p_mobj.c p_sight.c r_data.c r_draw.c r_plane.c tables.c w_wad.c z_zone.c; do
      ia16-elf-gcc -c \$f \$RENDER_OPTIONS \$CC_FLAGS
    done

    # Link everything
    LINK_FLAGS=\"-march=${CPU} -mcmodel=medium -li86 -mnewlib-nano-stdio -Os -fomit-frame-pointer -fgcse-sm -fgcse-las -fipa-pta -mregparmcall -flto -fwhole-program -funroll-all-loops -fira-loop-pressure -funsafe-loop-optimizations -freorder-blocks-algorithm=stc -fno-tree-pre -fira-region=mixed\"

    ia16-elf-gcc \\
      a_pcfx.c a_taskmn.c am_map.c d_items.c d_main.c f_finale.c f_libt.c \\
      g_game.c hu_text.c i_audio.c i_main.c i_system.c \\
      i_vtext.o i_vtexta.o info.c m_cheat.c m_fixed.o m_text.c m_random.c \\
      p_doors.c p_enemy.c p_enemy2.o p_floor.c p_inter.c p_lights.c \\
      p_map.o p_maputl.o p_mobj.o p_plats.c p_pspr.c p_setup.c p_sight.o \\
      p_spec.c p_switch.c p_telept.c p_tick.c p_user.c \\
      r_data.o r_draw.o r_plane.o r_sky.c r_things.c \\
      s_sound.c sounds.c st_pal.c st_text.c tables.o v_video.c w_wad.o \\
      wi_libt.c wi_stuff.c z_bmallo.c z_xms.o z_zone.o \\
      \$RENDER_OPTIONS \$LINK_FLAGS -o /build/output/${OUTPUT}

    # Clean up object files
    rm -f *.o

    echo 'Build complete: ${OUTPUT}'
  "

echo "Output: ${SCRIPT_DIR}/${OUTPUT}"

# Extract binary info
docker run --rm \
  -v "${SCRIPT_DIR}:/build/output" \
  doom-css-build \
  bash -c "
    ia16-elf-size /build/output/${OUTPUT} 2>/dev/null || true
    ia16-elf-objdump -Mi8086 -Mintel -fd /build/output/${OUTPUT} > /build/output/doom_disasm.txt 2>/dev/null || true
    echo 'Disassembly saved to doom_disasm.txt'
  "
