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
    vel_path = build / f"{args.prefix}string_vel_out.wav"
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

    def load_wav(path: Path) -> np.ndarray | None:
        if not path.exists():
            return None
        _, d = wavfile.read(path)
        if d.dtype.kind in "iu":
            d = d.astype(float) / np.iinfo(d.dtype).max
        else:
            d = d.astype(float)
        return d

    data = load_wav(wav_path)
    if data is None:
        sys.exit(f"*** {wav_path} not found — run `make run-seestr` first")
    vel_data = load_wav(vel_path)

    usable_frames = min(nframes, len(data) // M)
    if vel_data is not None:
        usable_frames = min(usable_frames, len(vel_data) // M)

    fig, ax = plt.subplots()
    plt.subplots_adjust(bottom=0.22)
    ymin = float(data.min())
    ymax = float(data.max())
    if vel_data is not None:
        ymin = min(ymin, float(vel_data.min()))
        ymax = max(ymax, float(vel_data.max()))
    yspan = max(ymax - ymin, 1e-12)
    ax.set_xlim(0, M - 1)
    ax.set_ylim(ymin - 0.05 * yspan, ymax + 0.05 * yspan)
    ax.set_xlabel("position along string (spatial samples)")
    ax.set_ylabel("displacement / velocity")
    ax.axhline(0.0, color="0.6", lw=0.8, ls="-", zorder=0)
    if beta is not None:
        ax.axvline(beta * M, color="saddlebrown", alpha=0.7, lw=1.5, ls="--",
                   label=f"bow (β={beta:.3f})")
    xs = np.arange(M)
    (line,) = ax.plot(xs, data[:M], color="tab:blue",
                      marker="*", markersize=4, label="displacement")
    vel_line = None
    if vel_data is not None:
        (vel_line,) = ax.plot(xs, vel_data[:M], color="tab:red",
                              marker="*", markersize=4, label="velocity")
    ax.legend(loc="upper right", fontsize=8)
    title = ax.set_title("")

    slider_ax = plt.axes([0.15, 0.08, 0.7, 0.04])
    speed_slider = Slider(
        ax=slider_ax, label="ms/frame", valmin=1, valmax=200, valinit=50, valstep=1
    )
    fig.text(
        0.5, 0.015,
        "[space] pause/resume     [←/→] step frame (while paused)",
        ha="center", va="bottom", fontsize=11, color="0.25",
    )

    hdr = f"f1={freq:.1f}Hz"
    if beta is not None:
        hdr += f"  β={beta:.3f}"

    def update(frame: int):
        start = frame * M
        line.set_ydata(data[start : start + M])
        if vel_line is not None:
            vel_line.set_ydata(vel_data[start : start + M])
        title.set_text(
            f"{hdr}   t = {frame*dt*1e3:7.3f} / {total_t*1e3:7.3f} ms   "
            f"(frame {frame}/{usable_frames})"
        )
        return line, title

    state = {"paused": False, "frame": 0}

    def track_frame(frame: int):
        state["frame"] = frame
        return update(frame)

    ani = FuncAnimation(
        fig, track_frame, frames=usable_frames, interval=50, blit=False, repeat=True
    )
    speed_slider.on_changed(lambda v: setattr(ani.event_source, "interval", float(v)))

    def step(delta: int):
        state["frame"] = (state["frame"] + delta) % usable_frames
        update(state["frame"])
        fig.canvas.draw_idle()

    def on_key(event):
        if event.key == " ":
            if state["paused"]:
                ani.event_source.start()
            else:
                ani.event_source.stop()
            state["paused"] = not state["paused"]
        elif event.key == "right" and state["paused"]:
            step(+1)
        elif event.key == "left" and state["paused"]:
            step(-1)

    fig.canvas.mpl_connect("key_press_event", on_key)

    plt.show()


if __name__ == "__main__":
    main()
