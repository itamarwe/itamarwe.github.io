"""
Microphone-array geometry + far-field response library.

Context: acoustic FPV-drone detection, band 300-4000 Hz, M=16 channels,
edge inference (Hailo / Jetson). The downstream algorithm is a *multichannel*
detector/classifier (not necessarily classic beamforming), so besides the
conventional delay-and-sum beam pattern we also quantify the spatial-sampling
diversity (the co-array) that such a network can exploit.

All geometry generators take `aperture` = maximum physical extent in metres
(diameter for planar/volumetric layouts, total length for the line) and return
an (M,3) array of microphone coordinates in metres.
"""
import numpy as np

C_SOUND = 343.0          # m/s, ~20 C dry air
M_DEFAULT = 16
GOLDEN = np.pi * (3.0 - np.sqrt(5.0))   # golden angle, rad


# --------------------------------------------------------------------------
# Geometries (all return (M,3) in metres, centred on origin)
# --------------------------------------------------------------------------
def ula(aperture, M=M_DEFAULT):
    x = np.linspace(-aperture / 2, aperture / 2, M)
    return np.column_stack([x, np.zeros(M), np.zeros(M)])


def uca(aperture, M=M_DEFAULT):
    R = aperture / 2
    a = np.arange(M) * 2 * np.pi / M
    return np.column_stack([R * np.cos(a), R * np.sin(a), np.zeros(M)])


def concentric(aperture, M=M_DEFAULT):
    """Center mic + nested rings. 16 = 1 + 5 + 10."""
    R = aperture / 2
    pts = [np.array([0.0, 0.0, 0.0])]
    rings = [(0.45 * R, 5), (R, 10)]
    for rad, n in rings:
        off = np.random.RandomState(0).rand()  # unused; kept deterministic
        a = np.arange(n) * 2 * np.pi / n + 0.3 * (rad / R)
        for ai in a:
            pts.append([rad * np.cos(ai), rad * np.sin(ai), 0.0])
    return np.array(pts[:M])


def spiral(aperture, M=M_DEFAULT):
    """Fermat/sunflower spiral: aperiodic, disk-filling, low grating lobes."""
    R = aperture / 2
    m = np.arange(M)
    r = R * np.sqrt((m + 0.5) / M)
    th = m * GOLDEN
    return np.column_stack([r * np.cos(th), r * np.sin(th), np.zeros(M)])


def random_planar(aperture, M=M_DEFAULT, seed=7):
    """Blue-noise-ish random disk layout (min-distance rejection sampling)."""
    R = aperture / 2
    rng = np.random.RandomState(seed)
    pts, tries = [], 0
    dmin = 0.7 * R / np.sqrt(M)
    while len(pts) < M and tries < 100000:
        tries += 1
        x, y = (rng.rand(2) * 2 - 1) * R
        if x * x + y * y > R * R:
            continue
        if all((x - px) ** 2 + (y - py) ** 2 > dmin ** 2 for px, py, _ in pts):
            pts.append([x, y, 0.0])
    return np.array(pts)


def dome(aperture, M=M_DEFAULT):
    """Hemispherical dome (Fibonacci hemisphere) -> elevation sensitivity."""
    R = aperture / 2
    m = np.arange(M)
    # z in (0, R], denser sampling kept off the pole
    z = (m + 0.5) / M                      # 0..1 -> sin(elevation)
    rho = np.sqrt(1 - z ** 2)
    th = m * GOLDEN
    return np.column_stack([R * rho * np.cos(th),
                            R * rho * np.sin(th),
                            R * z])


def nested_aperiodic(aperture, M=M_DEFAULT):
    """RECOMMENDED multi-scale planar layout: a tight central sunflower cluster
    (small baselines -> alias-light to 4 kHz) plus a wide aperiodic outrigger
    spread (large baselines -> low-frequency resolution). Best of both scales."""
    R = aperture / 2
    r_in = min(0.06, 0.18 * R)        # inner cluster ~<=6 cm radius
    n_in = 6
    n_out = M - n_in
    m = np.arange(n_in)
    r = r_in * np.sqrt((m + 0.5) / n_in)
    th = m * GOLDEN
    inner = np.column_stack([r * np.cos(th), r * np.sin(th), np.zeros(n_in)])
    m = np.arange(n_out)
    r = r_in + (R - r_in) * np.sqrt((m + 0.5) / n_out)
    th = m * GOLDEN + 1.7
    outer = np.column_stack([r * np.cos(th), r * np.sin(th), np.zeros(n_out)])
    return np.vstack([inner, outer])


def nested_dome(aperture, M=M_DEFAULT):
    """RECOMMENDED 3D layout: nested aperiodic plan lifted onto a shallow dome
    so out-of-plane baselines break the up/down (elevation) ambiguity that any
    flat array suffers — important for FPV threats that come from above."""
    p = nested_aperiodic(aperture, M).copy()
    R = aperture / 2
    rho = np.linalg.norm(p[:, :2], axis=1)
    # shallow dome: height falls off with radius (apex at centre)
    p[:, 2] = 0.45 * R * np.sqrt(np.clip(1 - (rho / (R + 1e-9)) ** 2, 0, 1))
    return p


def circular_aperiodic(aperture, M=M_DEFAULT, seed=3):
    """Single ring at the full radius but with non-uniform (jittered) angles:
    UCA-class resolution with the grating lobes broken into a diffuse floor.
    Matches the interactive explorer / histogram (perturbed-uniform, seed 3)."""
    R = aperture / 2
    rng = np.random.RandomState(seed)
    i = np.arange(M)
    ang = (i + 0.5 * rng.uniform(-1, 1, M)) * 2 * np.pi / M
    return np.column_stack([R * np.cos(ang), R * np.sin(ang), np.zeros(M)])


GEOMETRIES = {
    "ULA (line)":            ula,
    "UCA (single ring)":     uca,
    "Concentric rings":      concentric,
    "Spiral (sunflower)":    spiral,
    "Random planar":         random_planar,
    "Hemispherical dome":    dome,
}


# --------------------------------------------------------------------------
# Far-field response
# --------------------------------------------------------------------------
def direction(az, el=0.0):
    """Unit propagation direction(s) from azimuth/elevation (rad)."""
    az = np.asarray(az); el = np.asarray(el)
    return np.stack([np.cos(el) * np.cos(az),
                     np.cos(el) * np.sin(az),
                     np.sin(el) * np.ones_like(az)], axis=-1)


def steering(pos, u, f):
    """Steering vector(s): phase at each mic for plane wave from direction u.
    pos:(M,3) u:(...,3) -> (...,M) complex."""
    k = 2 * np.pi * f / C_SOUND
    return np.exp(1j * k * (u @ pos.T))


def beampattern_az(pos, f, az, az0=0.0, el=0.0, el0=0.0):
    """Conventional delay-and-sum power response (linear) over azimuth `az`,
    steered to (az0,el0). Returns array same shape as az."""
    u = direction(az, el)
    u0 = direction(np.array(az0), np.array(el0))
    d = steering(pos, u, f)               # (...,M)
    w = steering(pos, u0, f) / pos.shape[0]
    return np.abs(d @ np.conj(w)) ** 2


def directivity_index(pos, f, az0=0.0, el0=0.0, n=120):
    """Directivity (dB) of the DS beamformer by integrating power over sphere."""
    az = np.linspace(-np.pi, np.pi, 2 * n)
    el = np.linspace(-np.pi / 2, np.pi / 2, n)
    AZ, EL = np.meshgrid(az, el)
    u = direction(AZ, EL)                          # (n,2n,3)
    d = steering(pos, u, f)                         # (n,2n,M)
    w = steering(pos, direction(np.array(az0), np.array(el0)), f) / pos.shape[0]
    P = np.abs(d @ np.conj(w)) ** 2
    dOmega = np.cos(EL)
    avg = np.sum(P * dOmega) / np.sum(dOmega)
    return 10 * np.log10(1.0 / avg)


def main_and_sidelobe(pos, f, az0=0.0, el0=0.0, n=2048):
    """Return (-3dB beamwidth deg, peak-sidelobe level dB) in the az plane."""
    az = np.linspace(-np.pi, np.pi, n)
    P = beampattern_az(pos, f, az, az0=az0)
    P = P / P.max()
    PdB = 10 * np.log10(P + 1e-12)
    i0 = np.argmin(np.abs(az - az0))
    # walk out to -3 dB on both sides of main lobe
    def edge(step):
        i = i0
        while 0 < i < n - 1 and PdB[i] > -3:
            i += step
        return az[i]
    bw = np.degrees(edge(1) - edge(-1))
    # peak sidelobe: mask out the main lobe region
    main = np.abs(np.degrees(az - az0)) < max(bw, 4)
    psl = PdB[~main].max() if (~main).any() else -np.inf
    return abs(bw), psl


def coarray(pos):
    """All pairwise baseline vectors p_i - p_j (the co-array / difference set)."""
    diff = pos[:, None, :] - pos[None, :, :]
    return diff.reshape(-1, 3)


def baseline_lengths(pos):
    d = coarray(pos)
    L = np.linalg.norm(d, axis=1)
    return L[L > 1e-9]


def alias_free_freq(pos, plane_only=True):
    """Highest frequency with no spatial aliasing for a *uniform* read of the
    smallest baseline (spatial-Nyquist proxy): f = c / (2 * d_min)."""
    L = baseline_lengths(pos)
    dmin = L.min()
    return C_SOUND / (2 * dmin)


if __name__ == "__main__":
    for name, fn in GEOMETRIES.items():
        p = fn(0.4)
        L = baseline_lengths(p)
        print(f"{name:22s} M={len(p):2d} dmin={L.min()*100:5.1f}cm "
              f"dmax={L.max()*100:6.1f}cm  f_alias={alias_free_freq(p):6.0f}Hz "
              f"DI@2k={directivity_index(p,2000):4.1f}dB")
