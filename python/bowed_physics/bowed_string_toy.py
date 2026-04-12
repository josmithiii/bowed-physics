#!/usr/bin/env python3
"""
Toy bowed-string model: ideal string bowed by a rigid "stick".

Classic digital-waveguide bowed string (McIntyre/Schumacher/Woodhouse,
Smith).  The string is split at the bow contact into left and right
segments, each modeled by a pair of one-way delay lines.  The bow
junction is a velocity scattering with an injected friction force f;
the nut and bridge are rigid (-1) reflections with per-segment loss.

Friction model (simplest stick-slip):
    f_stick = 2 * Z * (v_bow - v_h)              # force needed to lock string to bow
    if |f_stick| <= mu_s * F_N:      stick  ->  f = f_stick
    else:                            slip   ->  f = sign(v_bow - v_h) * mu_d * F_N

Here v_h = v_L_in + v_R_in is the incoming-velocity sum at the bow
(the string velocity at the bow if no force were applied), and the
string velocity at the bow is v_h + f/(2Z).  With bow speed and force
in the Schelleng playability range, the junction entrains on the
string round-trip period and produces Helmholtz (sawtooth) motion.
"""

import argparse
from pathlib import Path

import matplotlib.animation as animation
import matplotlib.pyplot as plt
import numpy as np
from scipy.signal import welch

# ---------------------------------------------------------------------------
# Parameters
# ---------------------------------------------------------------------------
FS: int = 44100
DURATION: float = 1.0

# String
F0: float = 196.0          # open-string fundamental [Hz]  (~G3)
LOSS: float = 0.995        # one-way loss per segment traversal (round-trip = LOSS^4)
LP_A: float = 0.10         # one-pole lowpass coefficient at terminations (0 = none)
Y_LEAK: float = 0.9995     # leaky-integrator factor for display-only displacement
BETA: float = 1.0 / 8.0    # bow contact as fraction of string length from nut
Z: float = 0.55            # string transverse wave impedance [kg/s]  (toy value)

# Bow (rigid stick)
V_BOW: float = 0.10        # bow velocity [m/s]

# Bow-table reflection curve (STK-style, Smith 1986 / MSW 1983):
#   r(dv) = clamp( (|dv| * BOW_SLOPE + 0.75)^-4, BOW_R_MIN, BOW_R_MAX )
# with the bow junction injecting  newVelocity = dv * r(dv)  into each
# outgoing rail.  No explicit force or 2Z — this plays the role of the
# Friedlander–Keller graphical solution via a smooth lookup.
BOW_SLOPE: float = 3.0     # slope of the bow table; higher = sharper stick/slip transition
BOW_R_MIN: float = 0.01    # minimum reflection coefficient (fully slipping)
BOW_R_MAX: float = 0.98    # maximum reflection coefficient (quasi-stick, slightly absorptive)


def simulate(
    v_bow: float = V_BOW,
    beta: float = BETA,
    duration: float = DURATION,
    fs: int = FS,
    snapshot_interval: int = 0,
) -> tuple:
    """Run the digital-waveguide bowed-string simulation.

    Returns
    -------
    t : ndarray
        Time vector [s].
    v_string : ndarray
        Transverse string velocity at the bow contact point [m/s].
    snapshots : ndarray, optional
        Only returned if ``snapshot_interval > 0``.  Shape
        ``(n_frames, N_left + N_right)`` — transverse string
        displacement along the whole string at regular time intervals.
    x : ndarray, optional
        Normalized spatial positions (0 = nut, 1 = bridge) matching
        ``snapshots`` columns.  Returned only with snapshots.
    """
    N = int(duration * fs)
    t = np.arange(N) / fs

    # Delay-line lengths.  The total string round trip is fs/F0 samples,
    # i.e. one-way string length is fs/(2*F0) samples.  Split by beta.
    L_total = fs / (2.0 * F0)
    N_left = max(2, int(round(L_total * beta)))
    N_right = max(2, int(round(L_total * (1.0 - beta))))

    # Two delay lines per segment (upper / lower rails).
    #   a_*[-1] is the sample currently arriving at the bow
    #   b_*[-1] is the sample currently arriving at the far end (nut / bridge)
    a_left = np.zeros(N_left)    # nut -> bow
    b_left = np.zeros(N_left)    # bow -> nut
    a_right = np.zeros(N_right)  # bridge -> bow
    b_right = np.zeros(N_right)  # bow -> bridge

    v_string = np.zeros(N)
    dt = 1.0 / fs

    # One-pole lowpass state for each termination (realistic
    # frequency-dependent string loss: highs decay faster than lows).
    lp_nut = 0.0
    lp_bridge = 0.0
    a_lp = LP_A
    one_minus_a = 1.0 - a_lp

    # Displacement profile along the whole string (for animation).
    # Spatial layout: indices 0..N_left-1 span nut -> bow,
    # indices N_left..N_left+N_right-1 span bow -> bridge.
    y_profile = np.zeros(N_left + N_right)
    snapshots: list = []

    for n in range(N):
        # Waves currently arriving at the bow from each side
        v_L_in = a_left[-1]
        v_R_in = a_right[-1]
        v_h = v_L_in + v_R_in

        # Bow-table nonlinear reflection (Smith / McIntyre-Schumacher-
        # Woodhouse).  Smooth curve, no stick/slip branching.
        dv = v_bow - v_h
        r = (abs(dv) * BOW_SLOPE + 0.75) ** -4.0
        if r < BOW_R_MIN:
            r = BOW_R_MIN
        elif r > BOW_R_MAX:
            r = BOW_R_MAX
        delta = dv * r                                    # velocity injection at bow

        v_string[n] = v_h + delta

        # Outgoing waves from bow junction (velocity scattering + force injection)
        b_left_in = v_R_in + delta   # into left segment (bow -> nut)
        b_right_in = v_L_in + delta  # into right segment (bow -> bridge)

        # Reflections at rigid terminations (nut / bridge): -1 with loss,
        # followed by a one-pole lowpass so high frequencies decay faster.
        refl_nut = -LOSS * b_left[-1]
        lp_nut = one_minus_a * refl_nut + a_lp * lp_nut
        a_left_in = lp_nut

        refl_bridge = -LOSS * b_right[-1]
        lp_bridge = one_minus_a * refl_bridge + a_lp * lp_bridge
        a_right_in = lp_bridge

        # Propagate delay lines (shift by 1 sample; inject new samples at index 0)
        a_left[1:] = a_left[:-1]
        a_left[0] = a_left_in
        b_left[1:] = b_left[:-1]
        b_left[0] = b_left_in
        a_right[1:] = a_right[:-1]
        a_right[0] = a_right_in
        b_right[1:] = b_right[:-1]
        b_right[0] = b_right_in

        if snapshot_interval > 0:
            # Velocity at spatial sample i = upper rail + lower rail at that point.
            # Left segment: a_left[i] travels nut->bow (index 0 at nut),
            #               b_left[::-1][i] is the corresponding bow->nut rail.
            v_left = a_left + b_left[::-1]
            # Right segment: b_right[i] travels bow->bridge (index 0 at bow),
            #                a_right[::-1][i] is the corresponding bridge->bow rail.
            v_right = b_right + a_right[::-1]
            v_spatial = np.concatenate([v_left, v_right])
            # Leaky integrator: keeps the visualized profile from drifting
            # off-screen due to tiny DC residuals in the velocity field.
            y_profile = Y_LEAK * y_profile + v_spatial * dt
            if n % snapshot_interval == 0:
                snapshots.append(y_profile.copy())

    if snapshot_interval > 0:
        x = np.linspace(0.0, 1.0, N_left + N_right)
        return t, v_string, np.array(snapshots), x
    return t, v_string


def make_gif(
    beta: float = BETA,
    duration: float = 0.06,
    snapshot_interval: int = 8,
    fps: int = 30,
    out_path: Path = Path("png/fBowedStringToy.gif"),
) -> None:
    """Render a GIF of the string displacement profile over time."""
    t, _, snapshots, x = simulate(
        beta=beta, duration=duration, snapshot_interval=snapshot_interval
    )
    n_frames = snapshots.shape[0]
    y_max = float(np.max(np.abs(snapshots))) * 1.1 + 1e-9
    bow_x = beta

    fig, ax = plt.subplots(figsize=(9, 4))
    (line,) = ax.plot(x, snapshots[0], lw=1.8, color="C0")
    ax.axvline(bow_x, color="red", ls="--", lw=0.8, label="bow contact")
    ax.axhline(0.0, color="k", lw=0.4)
    ax.set_xlim(0.0, 1.0)
    ax.set_ylim(-y_max, y_max)
    ax.set_xlabel("Position along string (0 = nut, 1 = bridge)")
    ax.set_ylabel("Transverse displacement [m]")
    title = ax.set_title("")
    ax.legend(loc="upper right")
    ax.grid(alpha=0.3)

    dt_frame = snapshot_interval / FS

    def update(i: int):
        line.set_ydata(snapshots[i])
        title.set_text(
            f"Bowed string — Helmholtz motion forming   t = {i * dt_frame * 1e3:6.2f} ms"
        )
        return line, title

    anim = animation.FuncAnimation(
        fig, update, frames=n_frames, interval=1000.0 / fps, blit=False
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    anim.save(out_path, writer=animation.PillowWriter(fps=fps))
    print(f"Saved: {out_path}  ({n_frames} frames, {n_frames / fps:.1f} s)")
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--gif",
        action="store_true",
        help="Also render an animated GIF of the string-shape evolution",
    )
    parser.add_argument(
        "--beta",
        type=float,
        default=BETA,
        help=f"Bow contact position as a fraction of string length (default {BETA})",
    )
    parser.add_argument(
        "--suffix",
        type=str,
        default="",
        help="Suffix appended to output filenames (e.g. '_b3' for a 1/3 bow experiment)",
    )
    args = parser.parse_args()

    beta = args.beta
    if not (0.0 < beta < 1.0):
        raise SystemExit(f"*** --beta must be in (0, 1), got {beta}")
    suffix = args.suffix

    t, v = simulate(beta=beta)

    # Trim initial transient for the zoom plot
    n0 = int(0.3 * FS)
    n1 = n0 + int(0.04 * FS)  # show 40 ms

    # Spectrum (Welch) on the steady-state portion
    f, Pxx = welch(v[int(0.2 * FS):], fs=FS, nperseg=4096)
    Pxx_db = 10.0 * np.log10(Pxx + 1e-20)

    fig, axes = plt.subplots(2, 1, figsize=(10, 7))

    ax = axes[0]
    ax.plot(1000.0 * (t[n0:n1] - t[n0]), v[n0:n1], lw=1.0)
    ax.axhline(V_BOW, color="red", ls="--", lw=0.7, label=r"$v_\mathrm{bow}$")
    ax.set_xlabel("Time [ms]")
    ax.set_ylabel("String velocity at bow [m/s]")
    ax.set_title(
        f"Helmholtz motion: $F_0$={F0:.1f} Hz, "
        f"$\\beta$={beta:.3f}, $v_b$={V_BOW:.2f} m/s, bow slope={BOW_SLOPE:.1f}"
    )
    ax.legend(loc="upper right")
    ax.grid(alpha=0.3)

    ax = axes[1]
    mask = f <= 4000.0
    ax.plot(f[mask], Pxx_db[mask], lw=0.8)
    for k in range(1, 21):
        fk = k * F0
        if fk <= 4000.0:
            ax.axvline(fk, color="cyan", ls="--", lw=0.4, alpha=0.6)
    ax.set_xlabel("Frequency [Hz]")
    ax.set_ylabel("PSD [dB]")
    ax.set_title("Steady-state spectrum (cyan = harmonics of $F_0$)")
    ax.grid(alpha=0.3)

    plt.tight_layout()

    for out in (
        Path(f"png/fBowedStringToy{suffix}.png"),
        Path(f"eps/fBowedStringToy{suffix}.eps"),
    ):
        out.parent.mkdir(parents=True, exist_ok=True)
        plt.savefig(out, dpi=150)
        print(f"Saved: {out}")
    plt.close()

    if args.gif:
        make_gif(beta=beta, out_path=Path(f"png/fBowedStringToy{suffix}.gif"))


if __name__ == "__main__":
    main()
