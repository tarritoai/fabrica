"""Generate the paper texture of the 2D factory (plantilla-2d/remotion/src/kit/papel.png): a seamless 512×512 tile
of grain, soft mottling and a few fibres, made from seeded noise (CC0, no samples of anybody).

    uv run --with numpy --with pillow python tools/gen_papel.py

The tile is grey around 50 %: the reel lays it over everything with mix-blend-mode multiply/overlay at low opacity,
so it only adds texture, never colour. Filtering in the frequency domain makes the noise periodic: the tile repeats
without seams.
"""

from pathlib import Path

import numpy as np
from PIL import Image

N = 512
OUT = Path(__file__).resolve().parent.parent / "plantilla-2d" / "remotion" / "src" / "kit" / "papel.png"


def band(rng: np.random.Generator, low: float, high: float) -> np.ndarray:
    """Periodic noise with energy between two spatial frequencies (cycles per tile)."""
    f = np.fft.fftfreq(N) * N
    r = np.sqrt(f[:, None] ** 2 + f[None, :] ** 2)
    mask = np.exp(-((r - (low + high) / 2) ** 2) / (2 * ((high - low) / 2 + 1e-6) ** 2))
    spec = np.fft.fft2(rng.standard_normal((N, N))) * mask
    out = np.real(np.fft.ifft2(spec))
    return (out - out.mean()) / (out.std() + 1e-9)


def fibres(rng: np.random.Generator) -> np.ndarray:
    img = np.zeros((N, N))
    for _ in range(140):
        x, y = rng.uniform(0, N, 2)
        a = rng.uniform(0, np.pi)
        length = rng.uniform(10, 42)
        for t in np.linspace(0, length, int(length * 2)):
            px, py = int(x + np.cos(a) * t) % N, int(y + np.sin(a) * t) % N
            img[py, px] += 1
    return img


def main() -> None:
    rng = np.random.default_rng(7)
    grain = band(rng, 120, 250) * 0.55
    mottle = band(rng, 2, 9) * 0.9
    mid = band(rng, 18, 40) * 0.35
    fib = fibres(rng) * 0.8
    v = 128 + 9 * mottle + 7 * grain + 5 * mid - 10 * fib
    Image.fromarray(np.clip(v, 0, 255).astype(np.uint8), "L").save(OUT, optimize=True)
    print(f"{OUT} ({OUT.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
