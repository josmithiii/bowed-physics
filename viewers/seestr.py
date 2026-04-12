#!/usr/bin/env python3
"""
seestr.py — Python port of seestr.m from the 1997 appendix.

Reads build/{prefix}string_out.wav + build/{prefix}seestr_meta.txt
written by src/seestr.cpp and animates the bowed-string waveshape.
A ms/frame slider on the figure controls playback speed live.

Metadata format: `fs ilen stride nFrames freq [beta]`

Usage:
    python seestr.py                    # default experiment
    python seestr.py --prefix bow3_     # bow-at-1/3 experiment
"""

from __future__ import annotations

import argparse
import importlib.util
import sys
from pathlib import Path

import numpy as np
from matplotlib import pyplot as plt
from matplotlib.animation import FuncAnimation
from matplotlib.widgets import Slider
from scipy.io import wavfile

def load_meta(path: Path) -> dict:
    if not path.exists():
        sys.exit(f"*** {path} not found — run `make run-seestr` (or run-bow3) first")
    parts = path.read_text().split()
    if len(parts) < 5:
        sys.exit(f"*** {path}: expected at least 5 fields, got {len(parts)}")
    meta = {
        "fs": float(parts[0]),
        "ilen": int(parts[1]),
        "stride": int(parts[2]),
        "nframes": int(parts[3]),
        "freq": float(parts[4]),
    }
    if len(parts) >= 6:
        meta["beta"] = float(parts[5])
    return meta


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--prefix", default="", help="output-file prefix used by seestr")
    ap.add_argument("--build-dir", default="build", help="directory holding outputs")
    args = ap.parse_args()

    build = Path(args.build_dir)
    wav_path = build / f"{args.prefix}string_out.wav"
    meta_path = build / f"{args.prefix}seestr_meta.txt"

    meta = load_meta(meta_path)
    fs = meta["fs"]
    M = meta["ilen"]
    stride = meta["stride"]
    nframes = meta["nframes"]
    freq = meta["freq"]
    beta = meta.get("beta")
    dt = stride / fs
    total_t = nframes * dt

    _, data = wavfile.read(wav_path)
    if data.dtype.kind in "iu":
        data = data.astype(float) / np.iinfo(data.dtype).max
    else:
        data = data.astype(float)

    usable_frames = min(nframes, len(data) // M)

    fig, ax = plt.subplots()
    plt.subplots_adjust(bottom=0.22)
    ymin, ymax = float(data.min()), float(data.max())
    yspan = max(ymax - ymin, 1e-12)
    ax.set_xlim(0, M - 1)
    ax.set_ylim(ymin - 0.05 * yspan, ymax + 0.05 * yspan)
    ax.set_xlabel("position along string (spatial samples)")
    ax.set_ylabel("displacement")
    if beta is not None:
        ax.axvline(beta * M, color="tab:red", alpha=0.35, lw=1, ls="--",
                   label=f"bow (β={beta:.3f})")
        ax.legend(loc="upper right", fontsize=8)
    (line,) = ax.plot(np.arange(M), data[:M])
    title = ax.set_title("")

    slider_ax = plt.axes([0.15, 0.06, 0.7, 0.04])
    speed_slider = Slider(
        ax=slider_ax, label="ms/frame", valmin=1, valmax=200, valinit=50, valstep=1
    )

    hdr = f"f1={freq:.1f}Hz"
    if beta is not None:
        hdr += f"  β={beta:.3f}"

    def update(frame: int):
        start = frame * M
        line.set_ydata(data[start : start + M])
        title.set_text(
            f"{hdr}   t = {frame*dt*1e3:7.3f} / {total_t*1e3:7.3f} ms   "
            f"(frame {frame}/{usable_frames})"
        )
        return line, title

    ani = FuncAnimation(
        fig, update, frames=usable_frames, interval=50, blit=False, repeat=True
    )
    speed_slider.on_changed(lambda v: setattr(ani.event_source, "interval", float(v)))

    plt.show()


if __name__ == "__main__":
    main()
