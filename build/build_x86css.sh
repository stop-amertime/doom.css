#!/bin/bash
# Build Doom8088 for x86CSS — pure C, no ASM, no DOS dependencies.
#
# Prerequisites:
#   docker build -t doom-css-build build/

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"

WIDTH="${1:-40}"
HEIGHT="${2:-25}"
CPU="${3:-i8088}"
WAD_SEG="${4:-0xC000}"
OUTPUT="doom_x86css.com"

echo "Building Doom8088 for x86CSS: ${WIDTH}x${HEIGHT}, CPU=${CPU}, WAD_SEG=${WAD_SEG}"

docker run --rm \
  -v "${REPO_ROOT}/doom8088/src:/build/src" \
  -v "${SCRIPT_DIR}:/build/output" \
  -w /build/src \
  doom-css-build \
  bash -c "
    # All source files compiled together with LTO — no separate .o files.
    # Pure C: -DC_ONLY eliminates ASM dependencies, -DX86CSS adds platform stubs.

    ALL_FLAGS=\"-DX86CSS -DC_ONLY -DX86CSS_WAD_SEG=${WAD_SEG}\"
    ALL_FLAGS=\"\$ALL_FLAGS -DFLAT_SPAN -DFLAT_NUKAGE1_COLOR=32 -DFLAT_SKY_COLOR=7\"
    ALL_FLAGS=\"\$ALL_FLAGS -DWAD_FILE=\\\"DOOM16DT.WAD\\\"\"
    ALL_FLAGS=\"\$ALL_FLAGS -DVIEWWINDOWWIDTH=${WIDTH} -DVIEWWINDOWHEIGHT=${HEIGHT}\"
    ALL_FLAGS=\"\$ALL_FLAGS -DMAPWIDTH=${WIDTH} -DNR_OF_COLORS=16\"

    CC_FLAGS=\"-march=${CPU} -mcmodel=medium -mnewlib-nano-stdio -li86\"
    CC_FLAGS=\"\$CC_FLAGS -Os -fomit-frame-pointer -mregparmcall -fno-tree-pre\"

    # Single compilation unit — all .c files at once
    ia16-elf-gcc \\
      a_pcfx.c a_taskmn.c am_map.c d_items.c d_main.c f_finale.c f_libt.c \\
      g_game.c hu_text.c i_audio.c i_main.c i_system.c i_vtext.c \\
      info.c m_cheat.c m_text.c m_random.c \\
      p_doors.c p_enemy.c p_enemy2.c p_floor.c p_inter.c p_lights.c \\
      p_map.c p_maputl.c p_mobj.c p_plats.c p_pspr.c p_setup.c p_sight.c \\
      p_spec.c p_switch.c p_telept.c p_tick.c p_user.c \\
      r_data.c r_draw.c r_plane.c r_sky.c r_things.c \\
      s_sound.c sounds.c st_pal.c st_text.c tables.c v_video.c w_wad.c \\
      wi_libt.c wi_stuff.c z_bmallo.c z_zone.c \\
      \$ALL_FLAGS \$CC_FLAGS -o /build/output/${OUTPUT}

    echo 'Build complete: ${OUTPUT}'
  "

echo "Output: ${SCRIPT_DIR}/${OUTPUT}"
ls -la "${SCRIPT_DIR}/${OUTPUT}"
