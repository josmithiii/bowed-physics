# bowed-physics

Research and educational physical models of **bowed instruments** —
strings, resonators, and (eventually) plates. Mixed C++ / Python, with
the [Synthesis Toolkit (STK)](https://ccrma.stanford.edu/software/stk/)
vendored as a git submodule for the C++ side.

Author: Julius O. Smith III (CCRMA, Stanford).
License: [MIT](LICENSE). STK has its own permissive license under
`external/stk/`.

## Contents

| Path | What |
|---|---|
| `python/bowed_physics/bowed_string_toy.py` | Minimal digital-waveguide bowed string with STK-style BowTable reflection at the bow junction. Produces Helmholtz motion and an animated displacement GIF. |
| `cpp/src/seestr.cpp` | STK-based bowed-string probe driver (after the 1997 ICMC appendix). Writes a WAV audio file plus per-sample string-state snapshots. |
| `cpp/src/BowedProbe.cpp` / `cpp/include/bowed_physics/BowedProbe.h` | Subclass of `stk::Bowed` exposing the internal string state. |
| `viewers/seestr.py` | Matplotlib animation of the per-sample string-state WAV written by `seestr`. |

## Setup

```bash
git clone --recurse-submodules <url> bowed-physics
cd bowed-physics
# or, if you already cloned without --recurse-submodules:
git submodule update --init --recursive
```

Python deps (virtualenv recommended):

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e '.[dev]'
```

## Building

C++ targets go through CMake under `./build/`:

```bash
make configure      # cmake -S . -B build
make build          # cmake --build build
make seestr         # just the seestr experiment binary
```

## Running experiments

```bash
make help           # list all targets

# Python DW toy model
make bowed-string       # default β=1/8, near bridge
make bowed-string-b3    # β=1/3, segment ratio 1:2

# C++ STK-based probe
make run-seestr         # run simulation → build/*.wav + meta
make view-seestr        # animate the result
make run-bow3           # β=1/3 variant
make view-bow3
```

## Layout

```
bowed-physics/
├── CMakeLists.txt          # C++ build (uses external/stk submodule)
├── Makefile                # thin wrapper + Python/experiment targets
├── pyproject.toml          # Python package metadata
├── cpp/
│   ├── include/bowed_physics/   # public headers
│   └── src/                     # C++ sources
├── python/
│   └── bowed_physics/           # Python package
├── viewers/                     # Matplotlib viewers for experiment output
├── tests/                       # pytest
├── external/
│   └── stk/                     # git submodule → thestk/stk
└── docs/
```

## Status

Early. Being assembled from prior work:
- `bowed_string_toy.py` originated in `MUS420/BowedResonators/` lecture material.
- `seestr.cpp` / `BowedProbe` originated in an `ncbs` C++ port of the
  1997 ICMC appendix "Nonlinear Commuted Synthesis of Bowed Strings".

More physics (plates, resonator banks, LDV regime maps) will migrate
here over time.
