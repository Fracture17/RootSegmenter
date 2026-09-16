"""Reproduces the add segment segfault and checks that it stays fixed.

Connecting two far apart background points gives the search nothing bright to
follow, so crawlers spread in every direction and walk off the image.  Run from
the repository root.  Exits non-zero if the call crashes or corrupts memory.

Usage: python SCRIPTS/repro_two_point_crash.py
"""

import os
import sys

sys.path.insert(0, os.getcwd())

import numpy as np

from HumanCorrection import twoPointConnection

HEIGHT, WIDTH = 300, 300


def case(name, brightnesses, startPos, endPos):
    print(f"  {name}: {startPos} -> {endPos}", flush=True)
    result = twoPointConnection(startPos, endPos, brightnesses)
    assert result.shape == (HEIGHT, WIDTH), f"bad result shape {result.shape}"
    print(f"    returned, {int(result.sum())} pixels set", flush=True)


def main():
    rng = np.random.default_rng(0)

    #Uniform dim background with a little noise.  There is no root to follow.
    background = np.full((HEIGHT, WIDTH), 40, np.uint8)
    background += rng.integers(0, 5, background.shape, dtype=np.uint8)

    print("Background to background, far apart")
    case("opposite corners", background.copy(), (5, 5), (HEIGHT - 6, WIDTH - 6))
    case("across the top edge", background.copy(), (1, 1), (1, WIDTH - 2))
    case("down the left edge", background.copy(), (1, 1), (HEIGHT - 2, 1))

    print("\nStart and end hard against the border")
    case("corner to corner", background.copy(), (0, 0), (HEIGHT - 1, WIDTH - 1))

    print("\nA real root, which should succeed")
    withRoot = background.copy()
    withRoot[150, 20:280] = 200
    case("along a bright line", withRoot, (150, 20), (150, 279))

    print("\nNo crash.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
