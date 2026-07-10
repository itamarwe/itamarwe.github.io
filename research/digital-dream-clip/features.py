"""Extract per-video-frame audio features from pcm.wav using only numpy.

Outputs features.npz with, sampled at FPS:
  rms      : overall loudness envelope (0..1)
  low      : bass band energy (0..1)
  mid      : mid band energy (0..1)
  high     : treble band energy (0..1)
  bars     : (F, NBARS) log-frequency band energies (0..1) for the EQ
  beat     : per-frame beat impulse (0..1), decaying flash on detected onsets
  flux     : spectral flux / onset envelope (0..1)
"""
import sys, wave, struct
import numpy as np

FPS = 30
NBARS = 64

def read_wav(path):
    w = wave.open(path, "rb")
    n = w.getnframes(); sr = w.getframerate()
    raw = w.readframes(n); w.close()
    x = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
    return x, sr

def main():
    x, sr = read_wav("pcm.wav")
    dur = len(x) / sr
    nframes = int(dur * FPS)
    print(f"sr={sr} dur={dur:.2f}s frames={nframes}", file=sys.stderr)

    # STFT
    win = 2048
    hop = 512
    window = np.hanning(win).astype(np.float32)
    nhop = 1 + (len(x) - win) // hop
    stft = np.empty((nhop, win // 2 + 1), dtype=np.float32)
    for i in range(nhop):
        seg = x[i*hop:i*hop+win] * window
        stft[i] = np.abs(np.fft.rfft(seg))
    times = (np.arange(nhop) * hop + win/2) / sr  # sec per stft frame
    freqs = np.fft.rfftfreq(win, 1/sr)

    # spectral flux (onset envelope)
    diff = np.diff(stft, axis=0, prepend=stft[:1])
    flux = np.maximum(diff, 0).sum(axis=1)
    # normalize flux with a rolling-ish approach
    flux = flux / (np.percentile(flux, 99) + 1e-9)
    flux = np.clip(flux, 0, 1)

    # beat/onset detection: peak pick on flux
    def smooth(a, k):
        ker = np.ones(k)/k
        return np.convolve(a, ker, mode="same")
    fenv = smooth(flux, 5)
    thresh = smooth(fenv, 31) * 1.4 + 0.06
    peaks = []
    last = -10
    for i in range(1, len(fenv)-1):
        if fenv[i] > thresh[i] and fenv[i] >= fenv[i-1] and fenv[i] > fenv[i+1]:
            if i - last > int(0.12*sr/hop):  # min 120ms apart
                peaks.append(times[i]); last = i
    peaks = np.array(peaks)
    print(f"detected {len(peaks)} onsets", file=sys.stderr)

    # log-frequency bars
    fmin, fmax = 40, 12000
    edges = np.geomspace(fmin, fmax, NBARS+1)
    bar_idx = [np.where((freqs>=edges[b]) & (freqs<edges[b+1]))[0] for b in range(NBARS)]
    barmag = np.zeros((nhop, NBARS), dtype=np.float32)
    for b, idx in enumerate(bar_idx):
        if len(idx): barmag[:, b] = stft[:, idx].mean(axis=1)
    # log-compress
    barmag = np.log1p(barmag*8)
    # per-band normalize (so highs aren't invisible)
    barmag = barmag / (np.percentile(barmag, 98, axis=0, keepdims=True) + 1e-6)
    barmag = np.clip(barmag, 0, 1)

    # band energies
    def band(lo, hi):
        idx = np.where((freqs>=lo)&(freqs<hi))[0]
        e = stft[:, idx].mean(axis=1)
        e = np.log1p(e*8)
        return e / (np.percentile(e, 98)+1e-6)
    low  = np.clip(band(40, 250), 0, 1)
    mid  = np.clip(band(250, 2000), 0, 1)
    high = np.clip(band(2000, 12000), 0, 1)
    rms  = np.sqrt(smooth(x**2, 1024))
    # resample rms to stft times
    rms_st = np.interp(times, np.arange(len(rms))/sr, rms)
    rms_st = rms_st / (np.percentile(rms_st, 98)+1e-6)
    rms_st = np.clip(rms_st, 0, 1)

    # resample everything to video frame times
    vt = np.arange(nframes)/FPS
    def rs(a):
        if a.ndim == 1:
            return np.interp(vt, times, a).astype(np.float32)
        out = np.empty((nframes, a.shape[1]), dtype=np.float32)
        for c in range(a.shape[1]):
            out[:, c] = np.interp(vt, times, a[:, c])
        return out

    beat = np.zeros(nframes, dtype=np.float32)
    for p in peaks:
        fi = int(round(p*FPS))
        if 0 <= fi < nframes:
            beat[fi] = 1.0
    # decay flashes
    for i in range(1, nframes):
        beat[i] = max(beat[i], beat[i-1]*0.82)

    np.savez_compressed("features.npz",
        fps=FPS, nframes=nframes, dur=dur, nbars=NBARS,
        rms=rs(rms_st), low=rs(low), mid=rs(mid), high=rs(high),
        bars=rs(barmag), flux=rs(flux), beat=beat, peaks=peaks)
    print("saved features.npz", file=sys.stderr)

if __name__ == "__main__":
    main()
