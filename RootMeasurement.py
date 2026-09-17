"""Length measurement for skeletonized root segments.

Everything here works on an ordered path of skeleton pixels.  Turning a mask into
those paths is the job of the topology code, and is deliberately kept separate,
because the length estimate is verifiable on its own against shapes with known
lengths while the topology is not.

Two estimators are provided and both are reported.  Counting steps is exact for
straight horizontal, vertical, and 45 degree lines, but overestimates a shallow
line, because the skeleton renders it as a staircase of orthogonal runs.  Fitting
a spline first removes most of that bias.  When the two disagree by a lot, the
segment is noisy and worth looking at.
"""

from dataclasses import dataclass

import numpy as np
from scipy.interpolate import UnivariateSpline
from scipy.ndimage import convolve


DIAGONAL = 2 ** .5

#A skeleton pixel convolved with this kernel gives 10 plus its neighbour count,
#so 11 is a tip, 12 is a pass through, and 13 or more is a junction.
NEIGHBOR_KERNEL = np.array([
    [1, 1, 1],
    [1, 10, 1],
    [1, 1, 1],
])


@dataclass
class Length:
    stepped: float
    smoothed: float
    numPixels: int

    def disagreement(self) -> float:
        """Fraction the two estimators differ by.  A large value means a noisy path."""
        if self.stepped == 0:
            return 0.0
        return abs(self.smoothed - self.stepped) / self.stepped

    def inUnits(self, pixelsPerUnit: float) -> float:
        if pixelsPerUnit <= 0:
            raise ValueError(f"pixelsPerUnit must be positive, got {pixelsPerUnit}")
        return self.smoothed / pixelsPerUnit


def measurePath(path) -> Length:
    if len(path) < 2:
        return Length(0.0, 0.0, len(path))
    return Length(steppedLength(path), smoothedLength(path), len(path))


def steppedLength(path) -> float:
    """Sum of step distances, counting a diagonal step as root 2."""
    total = 0.0
    for a, b in zip(path, path[1:]):
        if a[0] != b[0] and a[1] != b[1]:
            total += DIAGONAL
        else:
            total += 1.0
    return total


def smoothedLength(path, samplesPerPixel: int = 4) -> float:
    """Arc length of a cubic spline fitted through the path.

    The spline parameters match smoothConnection, so a measured path is the same
    shape the add segment tool would have drawn.
    """
    if len(path) < 4:
        return steppedLength(path)

    T = np.arange(len(path))
    Y = [p[0] for p in path]
    X = [p[1] for p in path]
    W = [100] + [1] * (len(path) - 2) + [100]
    S = len(path) / 1.5

    splineY = UnivariateSpline(T, Y, w=W, s=S, k=3)
    splineX = UnivariateSpline(T, X, w=W, s=S, k=3)

    fine = np.linspace(T.min(), T.max(), len(path) * samplesPerPixel)
    return float(np.sum(np.hypot(np.diff(splineY(fine)), np.diff(splineX(fine)))))


def getNeighborCounts(skeleton: np.ndarray) -> np.ndarray:
    counts = convolve(skeleton.astype(np.uint8), NEIGHBOR_KERNEL, mode='constant', cval=0)
    return np.where(skeleton, counts, 0)


def getTips(skeleton: np.ndarray) -> list:
    counts = getNeighborCounts(skeleton)
    return [(int(r), int(c)) for r, c in np.argwhere(counts == 11)]


def getJunctions(skeleton: np.ndarray) -> list:
    counts = getNeighborCounts(skeleton)
    return [(int(r), int(c)) for r, c in np.argwhere(counts >= 13)]


def orderPath(skeleton: np.ndarray, start=None) -> list:
    """Orders one unbranched skeleton curve end to end.

    Raises if the skeleton branches, because an ordered path is not defined then
    and silently picking a direction would produce a wrong length.
    """
    junctions = getJunctions(skeleton)
    if junctions:
        raise ValueError(f"Skeleton branches at {len(junctions)} junction(s); split it into segments first")

    pixels = {(int(r), int(c)) for r, c in np.argwhere(skeleton)}
    if len(pixels) < 2:
        return sorted(pixels)

    if start is None:
        tips = getTips(skeleton)
        #A closed loop has no tips, so any pixel is a valid starting point.
        start = tips[0] if tips else min(pixels)

    path = [start]
    visited = {start}
    while True:
        nextPixel = None
        for neighbor in getNeighbors(path[-1]):
            if neighbor in pixels and neighbor not in visited:
                nextPixel = neighbor
                break
        if nextPixel is None:
            return path
        path.append(nextPixel)
        visited.add(nextPixel)


def getNeighbors(pos) -> list:
    """Orthogonal neighbours first, so a staircase is not walked diagonally when
    an orthogonal step is available."""
    r, c = pos
    orthogonal = [(r - 1, c), (r + 1, c), (r, c - 1), (r, c + 1)]
    diagonal = [(r - 1, c - 1), (r - 1, c + 1), (r + 1, c - 1), (r + 1, c + 1)]
    return orthogonal + diagonal
