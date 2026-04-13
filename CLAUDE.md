# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

Research/educational physical models of **bowed instruments** (strings, resonators, eventually plates). Mixed C++ / Python. Author: JOS (CCRMA). Early-stage; code is being migrated from prior projects (`MUS420/BowedResonators/`, `ncbs`, 1997 ICMC "Nonlinear Commuted Synthesis of Bowed Strings" appendix).

## Common commands

Build / run go through the top-level `Makefile`, which is a thin wrapper over CMake (C++) and direct `python3` calls (Python experiments / viewers).

```bash
make help                # list all targets
make configure           # cmake -S . -B build
make build               # build all C++ targets
make seestr              # build just the seestr binary
make rebuild             # clean + build
make clean               # rm -rf build/

make run-seestr          # run STK probe → build/string_out.wav + meta
make view-seestr         # animate it
make run-bow3            # β=1/3 variant
make view-bow3

make bowed-string        # Python DW toy, β=1/8
make bowed-string-b3     # Python DW toy, β=1/3

make test                # python3 -m pytest tests/
python3 -m pytest tests/test_foo.py::test_bar   # single test
```

Python deps: `pip install -e '.[dev]'` (numpy, scipy, matplotlib, pillow; pytest+ruff for dev).

First-time clone needs the STK submodule: `git submodule update --init --recursive`.

## Architecture

Two parallel implementation tracks of bowed-string physics that share the repo but not code:

1. **Python digital-waveguide toy** — `python/bowed_physics/bowed_string_toy.py`. Minimal DW model with STK-style BowTable reflection at the bow junction. Self-contained; produces PNG/EPS plus an animated displacement GIF. Entry point for pedagogy and quick experiments.

2. **C++ STK-based probe** — `cpp/src/seestr.cpp` drives `BowedProbe` (`cpp/{include,src}/.../BowedProbe.{h,cpp}`), a subclass of `stk::Bowed` that exposes the otherwise-private internal string state. Writes a normal audio WAV plus a per-sample string-state WAV that `viewers/seestr.py` animates. CLI args to `seestr`: `duration stride beta prefix`.

### CMake / STK build notes (non-obvious)

STK is vendored as a git submodule under `external/stk/`. We do **not** `add_subdirectory` it — STK's upstream CMake calls `find_package(CoreAudio)` which fails on stock macOS, and we don't need any real-time audio/MIDI backends. Instead `CMakeLists.txt` globs `external/stk/src/*.cpp`, removes the Rt*/Socket/Thread/Inet/MidiFile/Skini sources, and builds a minimal static `stk` target. Only `FileWvOut` is used for I/O, so no CoreAudio/ALSA/pthread linkage is needed. `BP_STK_RAWWAVES_PATH` is baked in at compile time pointing at `external/stk/rawwaves/` so binaries are relocatable within a source checkout.

If you need additional STK functionality, check whether the source you need was excluded by the `STK_EXCLUDE` list in `CMakeLists.txt` before adding new dependencies.

### Layout

- `python/bowed_physics/` — Python package (DW toy lives here).
- `cpp/include/bowed_physics/`, `cpp/src/` — public headers and C++ sources.
- `viewers/` — matplotlib animators that read experiment output from `build/`.
- `tests/` — pytest.
- `external/stk/` — git submodule (`thestk/stk`).
- `build/` — CMake build dir; experiment outputs (`*.wav`, meta files) also land here.
