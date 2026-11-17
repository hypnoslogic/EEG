#!/usr/bin/env python3
"""
make_figures.py — regenerates every illustrative figure on the EEG-for-anaesthetists site.

ALL SIGNALS ARE SYNTHETIC. They are built from band-limited noise so that each
"state" has the spectral shape described in the literature (Purdon et al. 2015;
Lee et al. 2021). They are teaching cartoons, not patient recordings.

The analysis deliberately mirrors eeg_rt_spectrum.py (the companion real-time tool):
  * Welch PSD, Hann window, 50 % overlap
  * SEF95 / median frequency over 0.5-45 Hz (SEF95 as in the script)
  * light theme colours and band colours, 'jet' colour map for the DSA
so that what learners see here is what they will see on the live tool.

Usage:  python make_figures.py            (writes PNGs into ../img)
Requires: numpy, scipy, matplotlib
"""
import os
import zlib
import numpy as np
from scipy import signal
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "img")
os.makedirs(OUT, exist_ok=True)
FS = 250.0           # Hz. Purdon et al. recorded at 250 Hz; high enough to show 50 Hz mains.
CMAP = "jet"
DSA_VMIN, DSA_VMAX = -20, 20     # one fixed dB scale so drug DSAs are directly comparable
FMAX = 40

# ---------------------------------------------------------------- theme (from eeg_rt_spectrum.py)
T = dict(surface="#fcfcfb", panel="#fcfcfb", text="#0b0b0b", text2="#52514e",
         muted="#8a8984", grid="#e4e3dd", raw="#0b0b0b", shade=0.16)
GREEK = {"slow": "S", "delta": "δ", "theta": "θ", "alpha": "α", "beta": "β", "gamma": "γ"}
BAND_COLOURS = {"slow": "#008300", "delta": "#2a78d6", "theta": "#eb6834", "alpha": "#1baf7a",
                "beta": "#eda100", "gamma": "#4a3aa7"}

# Band schemes as PUBLISHED. Purdon Table 1 lists integer ranges (slow <1, delta 1-4,
# theta 5-8, alpha 9-12, beta 13-25, gamma 26-80); for shading a continuous spectrum we use
# the contiguous edges 1/4/8/12/25. Lee et al. 2021 leave a gap at 12-14 Hz — shown as published.
SCHEMES = {
    "purdon": {"slow": (0.1, 1), "delta": (1, 4), "theta": (4, 8), "alpha": (8, 12),
               "beta": (12, 25), "gamma": (25, 80)},
    "lee": {"delta": (0.5, 4), "theta": (4, 8), "alpha": (8, 12), "beta": (14, 32),
            "gamma": (32, 80)},
}

plt.rcParams.update({
    "figure.facecolor": T["surface"], "axes.facecolor": T["panel"], "savefig.facecolor": T["surface"],
    "axes.edgecolor": T["grid"], "axes.labelcolor": T["text2"], "axes.titlecolor": T["text"],
    "text.color": T["text"], "xtick.color": T["muted"], "ytick.color": T["muted"],
    "xtick.labelcolor": T["text2"], "ytick.labelcolor": T["text2"], "grid.color": T["grid"],
    "axes.spines.top": False, "axes.spines.right": False, "axes.titlelocation": "left",
    "axes.titleweight": "bold", "axes.titlesize": 10, "axes.labelsize": 9,
    "xtick.labelsize": 8, "ytick.labelsize": 8, "font.size": 9, "font.family": "sans-serif",
    "font.sans-serif": ["Segoe UI", "Helvetica Neue", "Arial", "DejaVu Sans"],
})

RNG = np.random.default_rng(7)


# ---------------------------------------------------------------- signal building blocks
def osc(n, lo, hi, rms, rng=RNG):
    """Band-limited noise between lo and hi Hz with a given RMS (µV) — a realistic 'rhythm'."""
    w = rng.normal(0, 1, n + 2000)
    sos = signal.butter(2, [lo, hi], btype="bandpass", fs=FS, output="sos")   # gentle skirts, like real rhythms
    y = signal.sosfiltfilt(sos, w)[1000:-1000]
    y = y * envelope(n, rng.uniform(3, 12), 0.5, rng)
    return y / (y.std() + 1e-12) * rms


def pink(n, rms, rng=RNG):
    """1/f background (the 'floor' every real EEG has)."""
    f = np.fft.rfftfreq(n, 1 / FS)
    spec = rng.normal(size=f.size) + 1j * rng.normal(size=f.size)
    spec[1:] /= np.sqrt(f[1:]); spec[0] = 0
    spec[f > 47] *= 0.1                       # hardware anti-alias / monitor low-pass
    y = np.fft.irfft(spec, n)
    return y / y.std() * rms


def envelope(n, period_s, depth=0.6, rng=None):
    rng = rng if rng is not None else RNG
    """Slow amplitude modulation so rhythms wax and wane like real EEG."""
    t = np.arange(n) / FS
    ph = rng.uniform(0, 2 * np.pi)
    return 1 - depth / 2 + depth / 2 * np.sin(2 * np.pi * t / period_s + ph)


def state(name, dur, rng=RNG):
    """Return dur seconds of synthetic frontal EEG (µV) for a named brain state."""
    n = int(dur * FS)
    bg = pink(n, 5, rng)
    if name == "awake":            # eyes open: low amplitude, broadband beta/gamma
        return bg + osc(n, 14, 30, 4, rng) + osc(n, 30, 45, 2.5, rng)
    if name == "sedation":         # propofol sedation / paradoxical excitation: strong beta
        return bg + osc(n, 13, 24, 11, rng) * envelope(n, 3) + osc(n, 0.3, 3, 10, rng)
    if name == "propofol":         # surgical plane: slow-delta + coherent frontal alpha
        return (bg + osc(n, 0.2, 1.2, 28, rng) + osc(n, 1, 4, 16, rng)
                + osc(n, 9, 12, 14, rng) * envelope(n, 4, 0.4))
    if name == "induction":        # bolus induction: high-amplitude slow-delta, little else
        return bg + osc(n, 0.2, 1.2, 45, rng) + osc(n, 1, 4, 22, rng) + osc(n, 8, 12, 3, rng)
    if name == "sevo_sub":         # sub-MAC volatile: looks like propofol
        return (bg + osc(n, 0.2, 1.2, 24, rng) + osc(n, 1, 4, 15, rng)
                + osc(n, 8.5, 12, 13, rng) * envelope(n, 4, 0.4))
    if name == "sevo_mac":         # ≥1 MAC: theta fills in -> even power slow to alpha
        return (bg + osc(n, 0.2, 1.2, 24, rng) + osc(n, 1, 4, 16, rng)
                + osc(n, 4, 8, 13, rng) + osc(n, 8, 12, 13, rng))
    if name == "ketamine":         # high-beta/low-gamma 25-32 Hz + irregular slow
        return (bg + osc(n, 26, 33, 8, rng) * envelope(n, 5, 0.3) + osc(n, 0.3, 3, 14, rng)
                + osc(n, 4, 8, 4, rng))
    if name == "dex":              # slow-delta + intermittent 9-15 Hz spindles (1-2 s bursts)
        x = bg + osc(n, 0.3, 1.5, 18, rng) + osc(n, 1, 4, 10, rng)
        sp = osc(n, 11, 15, 1, rng)
        gate = np.zeros(n); t = 0.0
        while t < dur:
            t += rng.uniform(2.5, 6)
            L = rng.uniform(1, 2)
            i0, i1 = int(t * FS), int(min(dur, t + L) * FS)
            if i1 > i0:
                gate[i0:i1] = np.hanning(i1 - i0)
            t += L
        return x + 12 * sp * gate
    if name == "dex_deep":         # higher dex: spindles go, big slow-delta (like N3 sleep)
        return bg + osc(n, 0.3, 1.5, 32, rng) + osc(n, 1, 4, 16, rng)
    if name == "n2o_slow":         # switch to high-flow N2O: huge slow-delta, almost nothing >5 Hz
        return 0.4 * bg + osc(n, 0.5, 2, 55, rng) + osc(n, 2, 4, 10, rng)
    if name == "n2o_beta":         # established N2O: beta-gamma, lower amplitude
        return bg + osc(n, 20, 35, 6, rng) + osc(n, 0.5, 3, 6, rng)
    if name == "iso":              # isoelectric
        return pink(n, 0.8, rng)
    if name == "bs":               # burst suppression: propofol-like bursts in a flat background
        x = pink(n, 0.8, rng)
        t = rng.uniform(0, 2)
        while t < dur:
            L = rng.uniform(1.5, 3)
            i0, i1 = int(t * FS), int(min(dur, t + L) * FS)
            if i1 > i0:
                m = i1 - i0
                burst = (osc(m + 50, 0.5, 3, 40, rng)[:m] + osc(m + 50, 8, 12, 22, rng)[:m])
                x[i0:i1] += burst * np.hanning(m) ** 0.5
            t += L + rng.uniform(4, 9)
        return x
    raise ValueError(name)


# ---------------------------------------------------------------- analysis (mirrors eeg_rt_spectrum.analyse)
def welch(x, seg_s=2.0):
    x = signal.detrend(x)
    nper = int(seg_s * FS)
    return signal.welch(x, fs=FS, window="hann", nperseg=nper, noverlap=nper // 2)


def edge_freqs(f, p, lo=0.5, hi=45):
    m = (f >= lo) & (f <= hi)
    c = np.cumsum(p[m]); ff = f[m]
    return ff[np.searchsorted(c, 0.5 * c[-1])], ff[np.searchsorted(c, 0.95 * c[-1])]


def dsa(x, win_s=2.0, step_s=1.0):
    """Spectrogram -> dB. 2 s Hann windows, 1 s step (0.5 Hz resolution)."""
    nper = int(win_s * FS)
    f, t, S = signal.spectrogram(signal.detrend(x), fs=FS, window="hann", nperseg=nper,
                                 noverlap=nper - int(step_s * FS), mode="psd")
    return f, t, 10 * np.log10(S + 1e-6)


def shade(ax, scheme, fmax=FMAX, label=True):
    for name, (lo, hi) in SCHEMES[scheme].items():
        hi = min(hi, fmax)
        ax.axvspan(lo, hi, color=BAND_COLOURS[name], alpha=T["shade"], lw=0)
        if label:
            ax.text((lo + hi) / 2, 1.0, GREEK[name], transform=ax.get_xaxis_transform(), ha="center",
                    va="bottom", fontsize=9, color=BAND_COLOURS[name], weight="bold")


def plot_trace(ax, x, title=None, scale=50, dur=10):
    t = np.arange(len(x)) / FS
    ax.plot(t, x, color=T["raw"], lw=0.6)
    ax.set_xlim(0, dur); ax.set_ylim(-150, 120)
    ax.set_yticks([]); ax.set_xticks([])
    for s in ax.spines.values():
        s.set_visible(False)
    # scale bar
    ax.plot([dur * 0.985, dur * 0.985], [-140, -140 + scale], color=T["text2"], lw=1.2)
    ax.plot([dur * 0.885, dur * 0.985], [-140, -140], color=T["text2"], lw=1.2)
    ax.text(dur * 0.975, -140 + scale / 2, f"{scale} µV", ha="right", va="center", fontsize=7, color=T["text2"])
    ax.text(dur * 0.935, -146, "1 s", ha="center", va="top", fontsize=7, color=T["text2"])
    if title:
        ax.set_title(title, fontsize=9.5)


def plot_spectrum(ax, x, scheme, ylim=(-25, 25), show_edges=True):
    f, p = welch(x)
    k = f <= FMAX
    shade(ax, scheme)
    ax.plot(f[k], 10 * np.log10(p[k] + 1e-9), color=T["text"], lw=1.3)
    mf, sef = edge_freqs(f, p)
    if show_edges:
        ax.axvline(mf, ls=(0, (2, 2)), color=T["text2"], lw=1)
        ax.axvline(sef, ls=(0, (5, 3)), color=T["text2"], lw=1)
        ax.text(sef, 0.9, f" SEF95\n {sef:.1f} Hz", transform=ax.get_xaxis_transform(), fontsize=7, color=T["text2"], va="top")
        ax.text(mf, 0.62, f" MF\n {mf:.1f} Hz", transform=ax.get_xaxis_transform(), fontsize=7, color=T["text2"], va="top")
    ax.set_xlim(0, FMAX); ax.set_ylim(*ylim)
    ax.set_xlabel("Frequency (Hz)"); ax.set_ylabel("Power (dB)")
    ax.grid(axis="y", alpha=0.7)
    return mf, sef


def plot_dsa(ax, x, cax=None, fmax=FMAX, xlabel="Time (minutes)", vmin=DSA_VMIN, vmax=DSA_VMAX, minutes=True):
    f, t, S = dsa(x)
    k = f <= fmax
    tt = t / 60 if minutes else t
    im = ax.pcolormesh(tt, f[k], S[k], cmap=CMAP, vmin=vmin, vmax=vmax, shading="auto", rasterized=True)
    ax.set_ylabel("Frequency (Hz)"); ax.set_xlabel(xlabel); ax.set_ylim(0, fmax)
    if cax is not None:
        cb = plt.colorbar(im, cax=cax); cb.outline.set_visible(False)
        cax.set_title("dB", fontsize=8, color=T["text2"], loc="left"); cax.tick_params(length=0, labelsize=7)
    return im


def save(fig, name):
    fig.savefig(os.path.join(OUT, name), dpi=140, bbox_inches="tight")
    plt.close(fig)
    print("wrote", name)


# ---------------------------------------------------------------- figure 1: state gallery (raw traces)
def fig_gallery():
    rows = [("awake", "A  Awake, eyes open — low-amplitude beta/gamma"),
            ("sedation", "B  Sedation / paradoxical excitation — beta oscillations"),
            ("propofol", "C  Unconscious, surgical plane — slow-delta + alpha"),
            ("induction", "D  Unconscious at induction — slow oscillations"),
            ("bs", "E  Burst suppression — bursts separated by flat (suppressed) EEG"),
            ("iso", "F  Isoelectric — no cortical activity")]
    fig, axs = plt.subplots(len(rows), 1, figsize=(9, 9.6))
    for ax, (k, title) in zip(axs, rows):
        x = state(k, 10, np.random.default_rng(zlib.crc32(k.encode())))
        plot_trace(ax, x, title)
    fig.tight_layout(h_pad=0.6)
    save(fig, "gallery_states.png")


# ---------------------------------------------------------------- figure 2: anatomy of a spectrum
def fig_spectrum_anatomy(scheme):
    rng = np.random.default_rng(3)
    x = state("propofol", 30, rng)
    fig = plt.figure(figsize=(9, 6.2))
    gs = fig.add_gridspec(3, 1, height_ratios=[1, 0.9, 1.6], hspace=0.6)
    ax0 = fig.add_subplot(gs[0]); plot_trace(ax0, x[: int(10 * FS)], "A  10 s of raw EEG (propofol, surgical plane)")
    ax1 = fig.add_subplot(gs[1])
    t = np.arange(int(10 * FS)) / FS
    a = signal.sosfiltfilt(signal.butter(4, [8, 12], "bandpass", fs=FS, output="sos"), x)[: len(t)]
    s = signal.sosfiltfilt(signal.butter(4, [0.1, 4], "bandpass", fs=FS, output="sos"), x)[: len(t)]
    ax1.plot(t, s + 55, color=BAND_COLOURS["delta"], lw=1); ax1.plot(t, a - 35, color=BAND_COLOURS["alpha"], lw=0.9)
    ax1.text(10.05, 55, "slow-delta\n0.1–4 Hz", color=BAND_COLOURS["delta"], fontsize=8, va="center")
    ax1.text(10.05, -35, "alpha\n8–12 Hz", color=BAND_COLOURS["alpha"], fontsize=8, va="center")
    ax1.set_xlim(0, 10); ax1.axis("off"); ax1.set_title("B  The same trace band-pass filtered into its two main rhythms", fontsize=9.5)
    ax2 = fig.add_subplot(gs[2])
    plot_spectrum(ax2, x, scheme)
    ax2.set_title(f"C  Its power spectrum (Welch, 2 s Hann segments) — bands shaded: {'Purdon 2015' if scheme=='purdon' else 'Lee 2021'}", fontsize=9.5, pad=14)
    save(fig, f"spectrum_anatomy_{scheme}.png")


# ---------------------------------------------------------------- figure 3: per-drug panels
DRUGS = {
    "propofol": [("propofol", "Propofol — surgical plane")],
    "sevo": [("sevo_sub", "Sevoflurane < 1 MAC"), ("sevo_mac", "Sevoflurane ≥ 1 MAC (theta fills in)")],
    "ketamine": [("ketamine", "Ketamine — beta/gamma ~25–32 Hz")],
    "dex": [("dex", "Dexmedetomidine — light: slow-delta + spindles"), ("dex_deep", "Dexmedetomidine — deeper: slow-delta, spindles gone")],
    "n2o": [("n2o_slow", "N₂O switch (~4 min): large slow-delta, little >5 Hz"), ("n2o_beta", "Established N₂O: beta-gamma")],
}


def fig_drug(key, scheme):
    items = DRUGS[key]
    n = len(items)
    fig = plt.figure(figsize=(10, 2.9 * n))
    gs = fig.add_gridspec(n, 3, width_ratios=[1.35, 1, 1.15], wspace=0.32, hspace=0.85)
    row_axes = []
    for r, (st, title) in enumerate(items):
        x = state(st, 300, np.random.default_rng(zlib.crc32(st.encode())))
        ax = fig.add_subplot(gs[r, 0]); plot_trace(ax, x[: int(10 * FS)], "Raw EEG, 10 s")
        row_axes.append((ax, title))
        ax = fig.add_subplot(gs[r, 1]); plot_spectrum(ax, x, scheme, show_edges=True)
        ax.set_title("Spectrum", fontsize=9.5, pad=14)
        sub = gs[r, 2].subgridspec(1, 2, width_ratios=[20, 1], wspace=0.06)
        ax = fig.add_subplot(sub[0]); cax = fig.add_subplot(sub[1])
        plot_dsa(ax, x, cax); ax.set_title("DSA (5 min)", fontsize=9.5)
    for ax, title in row_axes:
        p = ax.get_position()
        fig.text(p.x0, p.y1 + 0.21 / n, title, fontsize=11.5, weight="bold", color=T["text"])
    save(fig, f"drug_{key}_{scheme}.png")


# ---------------------------------------------------------------- figure 4: whole-case DSA timeline
def fig_case():
    rng = np.random.default_rng(11)
    segs = [("awake", 3), ("induction", 3), ("bs", 3), ("propofol", 14), ("propofol_noci", 2),
            ("propofol", 8), ("sevo_mac", 7), ("sevo_sub", 5), ("emerge", 6), ("awake", 3)]
    parts = []
    for st, m in segs:
        d = m * 60
        if st == "propofol_noci":        # incision: alpha drop-out + beta arousal, then resolves
            x = state("propofol", d, rng)
            n = len(x); g = np.ones(n); g[int(0.15 * n):int(0.85 * n)] = 0.25
            beta = osc(n, 15, 28, 9, rng) * (1 - g)
            alpha = signal.sosfiltfilt(signal.butter(4, [8, 12.5], "bandpass", fs=FS, output="sos"), x)
            x = x - alpha * (1 - g) + beta
        elif st == "emerge":             # zipper: slow & alpha fade, beta/gamma return, alpha drifts up
            n = int(d * FS); fr = np.linspace(0, 1, n)
            x = (pink(n, 3, rng) + osc(n, 0.2, 1.2, 26, rng) * (1 - fr) ** 1.5
                 + osc(n, 1, 4, 14, rng) * (1 - fr) + osc(n, 9, 13, 13, rng) * (1 - fr) ** 1.2
                 + osc(n, 14, 30, 6, rng) * fr + osc(n, 30, 45, 3, rng) * fr)
        else:
            x = state(st, d, rng)
        parts.append(x)
    x = np.concatenate(parts)
    f, t, S = dsa(x)
    k = f <= FMAX
    fig = plt.figure(figsize=(11, 4.8))
    gs = fig.add_gridspec(1, 2, width_ratios=[60, 1], wspace=0.02)
    ax = fig.add_subplot(gs[0]); cax = fig.add_subplot(gs[1])
    im = ax.pcolormesh(t / 60, f[k], S[k], cmap=CMAP, vmin=DSA_VMIN, vmax=DSA_VMAX, shading="auto", rasterized=True)
    cb = plt.colorbar(im, cax=cax); cb.outline.set_visible(False); cax.set_title("dB", fontsize=8, loc="left")
    # MF and SEF95 trends (smoothed over 15 s)
    P = 10 ** (S / 10); m = (f >= 0.5) & (f <= 45)
    c = np.cumsum(P[m], axis=0); ff = f[m]
    mf = ff[np.argmax(c >= 0.5 * c[-1], axis=0)]; sef = ff[np.argmax(c >= 0.95 * c[-1], axis=0)]
    sm = lambda v: np.convolve(v, np.ones(15) / 15, mode="same")
    ax.plot(t / 60, sm(sef), color="white", lw=1.4); ax.plot(t / 60, sm(mf), color="white", lw=1.4, ls=(0, (3, 2)))
    ax.text(11, 36, "SEF95 (solid) · median frequency (dashed)", color="white", fontsize=8)
    edges = np.cumsum([0] + [m for _, m in segs])
    labels = ["Awake", "Bolus", "BS", "Propofol maintenance", "Incision", "", "Sevo ≥1 MAC", "Sevo <1 MAC", "Emergence", "Awake"]
    for e0, e1, lab in zip(edges[:-1], edges[1:], labels):
        ax.axvline(e1, color="white", lw=0.6, alpha=0.5)
        if lab:
            ax.text((e0 + e1) / 2, FMAX + 1, lab, ha="center", va="bottom", fontsize=7.5, color=T["text"])
    ax.set_xlim(0, edges[-1]); ax.set_ylim(0, FMAX)
    ax.set_xlabel("Time (minutes)"); ax.set_ylabel("Frequency (Hz)")
    ax.set_title("A synthetic anaesthetic, start to finish", pad=18)
    save(fig, "case_timeline.png")


# ---------------------------------------------------------------- figure 5: burst suppression & SR
def fig_bs():
    rng = np.random.default_rng(5)
    x = state("bs", 60, rng)
    t = np.arange(len(x)) / FS
    env = np.abs(signal.hilbert(signal.sosfiltfilt(signal.butter(4, [0.5, 30], "bandpass", fs=FS, output="sos"), x)))
    env = np.convolve(env, np.ones(int(0.25 * FS)) / int(0.25 * FS), mode="same")
    supp = env < 5
    # suppressed epochs must last ≥0.5 s
    lab, start = supp.copy(), None
    for i, v in enumerate(np.append(supp, False)):
        if v and start is None: start = i
        if not v and start is not None:
            if i - start < 0.5 * FS: lab[start:i] = False
            start = None
    sr = lab.mean() * 100
    fig, axs = plt.subplots(2, 1, figsize=(10, 4.6), sharex=True, gridspec_kw=dict(height_ratios=[2, 1], hspace=0.25))
    ax = axs[0]
    ax.plot(t, x, color=T["raw"], lw=0.5)
    ax.axhline(5, color="#e34948", lw=0.8); ax.axhline(-5, color="#e34948", lw=0.8)
    ax.set_ylim(-60, 60); ax.set_ylabel("µV")
    ax.set_title(f"Burst suppression, 60 s — suppression ratio (SR) ≈ {sr:.0f} %   (red lines: ±5 µV threshold)")
    ax2 = axs[1]
    ax2.fill_between(t, 0, lab.astype(float), step="mid", color="#2a78d6", alpha=0.6, lw=0)
    ax2.set_yticks([0, 1], ["burst", "suppressed"]); ax2.set_xlabel("Time (s)"); ax2.set_xlim(0, 60)
    save(fig, "burst_suppression.png")
    return sr


# ---------------------------------------------------------------- figure 6: artefacts (ShARP)
def fig_artefacts():
    rng = np.random.default_rng(21)
    base = lambda d: state("propofol", d, rng)
    d = 60; n = int(d * FS); t = np.arange(n) / FS
    arts = {}
    # EMG: broadband high-frequency, rising into RE-only range
    x = base(d); g = (t > 20) & (t < 45)
    arts["EMG (muscle)"] = x + g * osc(n, 25, 47, 14, rng)
    # ECG: spiky, ~1.2/s, regular
    x = base(d); ecg = np.zeros(n)
    for b in np.arange(0.3, d, 0.83):
        i = int(b * FS); w = int(0.06 * FS)
        if i + w < n: ecg[i:i + w] += 45 * signal.windows.gaussian(w, w / 8)
    arts["ECG"] = x + ecg
    # Eye movement / blink: big slow deflections
    x = base(d)
    for b in [1.5, 4.2, 7.8, 13, 21, 29, 37, 44, 52]:
        i = int(b * FS); w = int(0.45 * FS)
        if i + w < n: x[i:i + w] += 160 * np.hanning(w)
    arts["Eye movement / blink"] = x
    # Mains interference 50 Hz (only visible if sampling > 100 Hz)
    x = base(d); arts["50 Hz mains"] = x + ((t > 15) & (t < 50)) * 12 * np.sin(2 * np.pi * 50 * t)
    # Electrocautery: bursts of huge broadband, clipping
    x = base(d)
    for b in [10, 26, 41]:
        i0, i1 = int(b * FS), int((b + 4) * FS); x[i0:i1] += rng.normal(0, 150, i1 - i0)
    arts["Diathermy"] = np.clip(x, -200, 200)
    # Electrode pop / poor contact: step + drift
    x = base(d); i = int(25 * FS)
    x[i:] += 70 * np.exp(-(t[i:] - 25) / 3); x[int(40 * FS):int(42 * FS)] = 0.2 * rng.normal(0, 1, int(2 * FS))
    arts["Electrode pop / lift"] = x

    fig = plt.figure(figsize=(11, 2.3 * len(arts)))
    gs = fig.add_gridspec(len(arts), 3, width_ratios=[1.4, 1.4, 0.05], wspace=0.15, hspace=0.75)
    for r, (name, x) in enumerate(arts.items()):
        ax = fig.add_subplot(gs[r, 0])
        seg = {"EMG (muscle)": 25, "ECG": 5, "Eye movement / blink": 0, "50 Hz mains": 20,
               "Diathermy": 8, "Electrode pop / lift": 22}[name]
        xs = x[int(seg * FS): int((seg + 10) * FS)]
        ax.plot(np.arange(len(xs)) / FS, xs, color=T["raw"], lw=0.5)
        ax.set_xlim(0, 10); lim = 200 if name in ("Diathermy", "Eye movement / blink") else 120; ax.set_ylim(-lim, lim)
        ax.set_title(f"{name} — raw (10 s)", fontsize=9.5); ax.set_ylabel("µV"); ax.set_xlabel("s")
        ax = fig.add_subplot(gs[r, 1]); cax = fig.add_subplot(gs[r, 2])
        plot_dsa(ax, x, cax, fmax=60, xlabel="Time (s)", minutes=False)
        ax.axhline(47, color="white", lw=0.6, ls=(0, (2, 2)))
        ax.set_title("DSA (60 s)", fontsize=9.5)
    save(fig, "artefacts.png")


# ---------------------------------------------------------------- figure 7: age effect
def fig_age(scheme):
    rng = np.random.default_rng(31)
    n = int(120 * FS)
    young = pink(n, 4, rng) + osc(n, 0.2, 1.2, 32, rng) + osc(n, 1, 4, 18, rng) + osc(n, 9, 12, 18, rng)
    old = pink(n, 2.5, rng) + osc(n, 0.2, 1.2, 18, rng) + osc(n, 1, 4, 10, rng) + osc(n, 8, 11, 5, rng)
    fig, axs = plt.subplots(1, 2, figsize=(10, 3.4), gridspec_kw=dict(width_ratios=[1.3, 1], wspace=0.28))
    ax = axs[0]
    for x, lab, c in [(young, "30-year-old (illustrative)", "#2a78d6"), (old, "80-year-old (illustrative)", "#eb6834")]:
        f, p = welch(x); k = f <= FMAX
        ax.plot(f[k], 10 * np.log10(p[k]), color=c, lw=1.4, label=lab)
    shade(ax, scheme); ax.set_xlim(0, FMAX); ax.set_ylim(-25, 25)
    ax.set_xlabel("Frequency (Hz)"); ax.set_ylabel("Power (dB)"); ax.legend(frameon=False, loc="upper right")
    ax.set_title("Same propofol dose, different ages", pad=14)
    ax = axs[1]
    t = np.arange(int(10 * FS)) / FS
    ax.plot(t, young[: len(t)] + 60, color="#2a78d6", lw=0.5); ax.plot(t, old[: len(t)] - 60, color="#eb6834", lw=0.5)
    ax.set_yticks([60, -60], ["young", "old"]); ax.set_xlabel("s"); ax.set_ylim(-140, 140)
    ax.set_title("Raw EEG — note the lower amplitude", fontsize=9.5)
    save(fig, f"age_{scheme}.png")


# ---------------------------------------------------------------- figure 8: same number, different brain
def fig_same_number():
    rng = np.random.default_rng(41)
    pairs = [("propofol", "Propofol, unconscious"), ("ketamine", "Ketamine, unconscious"),
             ("dex_deep", "Dexmedetomidine, rousable")]
    fig, axs = plt.subplots(2, 3, figsize=(11, 4.6), gridspec_kw=dict(height_ratios=[1, 1.2], hspace=0.55, wspace=0.3))
    for c, (st, lab) in enumerate(pairs):
        x = state(st, 60, rng)
        plot_trace(axs[0, c], x[: int(10 * FS)], lab)
        mf, sef = plot_spectrum(axs[1, c], x, "purdon")
        axs[1, c].set_title(f"SEF95 {sef:.0f} Hz", fontsize=9.5, pad=14)
    save(fig, "same_number_different_brain.png")


# ---------------------------------------------------------------- figure 9: window length vs resolution
def fig_resolution():
    rng = np.random.default_rng(51)
    n = int(60 * FS); t = np.arange(n) / FS
    x = pink(n, 3, rng) + 15 * np.sin(2 * np.pi * 10 * t) + 15 * np.sin(2 * np.pi * 11.5 * t) + osc(n, 0.3, 1.2, 20, rng)
    fig, axs = plt.subplots(1, 3, figsize=(11, 3.1), sharey=True)
    for ax, seg in zip(axs, [0.5, 2, 8]):
        f, p = welch(x, seg); k = f <= 20
        ax.plot(f[k], 10 * np.log10(p[k]), color=T["text"], lw=1.2, marker="o" if seg < 1 else None, ms=3)
        ax.set_title(f"Segment {seg:g} s → Δf = {1/seg:g} Hz", fontsize=9.5)
        ax.set_xlabel("Frequency (Hz)"); ax.set_xlim(0, 20); ax.grid(axis="y", alpha=0.7)
        ax.axvline(10, color=BAND_COLOURS["alpha"], lw=0.8, ls=":"); ax.axvline(11.5, color=BAND_COLOURS["alpha"], lw=0.8, ls=":")
    axs[0].set_ylabel("Power (dB)")
    fig.suptitle("Two alpha rhythms 1.5 Hz apart: only longer segments separate them (at the cost of time-resolution)", fontsize=9.5, x=0.01, ha="left")
    save(fig, "window_resolution.png")


# ---------------------------------------------------------------- figure 10: nociception patterns
def fig_nociception():
    rng = np.random.default_rng(61)
    d = 300; parts = []
    x = state("propofol", d, rng); n = len(x); t = np.arange(n) / FS
    g = np.clip((t - 100) / 10, 0, 1) * np.clip((220 - t) / 20, 0, 1)   # stimulus window 100-220 s
    alpha = signal.sosfiltfilt(signal.butter(4, [8, 12.5], "bandpass", fs=FS, output="sos"), x)
    x1 = x - 0.8 * alpha * g + osc(n, 15, 28, 8, rng) * g                # alpha drop-out + beta arousal
    xb = (pink(n, 4, rng) + osc(n, 0.2, 1.2, 10, rng) + osc(n, 1, 4, 7, rng)
          + osc(n, 8.5, 12, 12, rng))                                      # lighter-slow baseline
    a2 = signal.sosfiltfilt(signal.butter(4, [8, 12.5], "bandpass", fs=FS, output="sos"), xb)
    x2 = xb - 0.5 * a2 * g + osc(n, 0.5, 3, 40, rng) * g                 # paradoxical delta arousal
    fig = plt.figure(figsize=(10, 4.2))
    gs = fig.add_gridspec(1, 3, width_ratios=[20, 20, 1], wspace=0.15)
    for c, (xx, ttl) in enumerate([(x1, "Alpha drop-out ± beta arousal"), (x2, "'Paradoxical' delta arousal")]):
        ax = fig.add_subplot(gs[c]); plot_dsa(ax, xx, fig.add_subplot(gs[2]) if c == 1 else None)
        ax.axvspan(100 / 60, 220 / 60, ymin=0.97, ymax=1, color="#e34948")
        if c == 1: ax.set_ylabel("")
        ax.set_title(f"{ttl}\n(red bar = surgical stimulus)", fontsize=9.5)
    save(fig, "nociception.png")


if __name__ == "__main__":
    fig_gallery()
    for s in SCHEMES:
        fig_spectrum_anatomy(s)
        for k in DRUGS:
            fig_drug(k, s)
        fig_age(s)
    fig_case()
    sr = fig_bs()
    fig_artefacts()
    fig_same_number()
    fig_resolution()
    fig_nociception()
