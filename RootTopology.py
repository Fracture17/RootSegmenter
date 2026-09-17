"""Turns a binary root mask into a graph of segments, junctions, and tips.

The graph is built from the mask alone.  Nothing here looks at the original
image, because the geometry needed to separate a crossing from a branch is
already present in the mask: the direction each arm leaves a junction, and how
thick each arm is.

This stage deliberately makes no judgement about which segments belong to the
same root.  It reports what is there, so the result can be drawn and checked
before any heuristic decides what it means.
"""

from dataclasses import dataclass, field

import numpy as np
from scipy.ndimage import distance_transform_edt
from skimage import morphology
from skimage.measure import label as labelComponents

from RootMeasurement import Length, measurePath, orderPath, getNeighborCounts


@dataclass
class Segment:
    """One unbranched run of skeleton between two nodes, a node and a tip, or two tips."""
    path: list
    length: Length
    meanWidth: float
    maxWidth: float
    nodes: list = field(default_factory=list)

    def ends(self):
        return self.path[0], self.path[-1]

    def heading(self, atEnd, sampleLength: int = 8):
        """Direction the segment leaves one of its ends, in radians.

        Taken from a short run near the end rather than the single last step, so a
        staircase does not produce a meaningless angle.
        """
        path = self.path if atEnd == self.path[0] else self.path[::-1]
        far = path[min(sampleLength, len(path) - 1)]
        return float(np.arctan2(far[0] - path[0][0], far[1] - path[0][1]))


@dataclass
class RootGraph:
    segments: list
    junctions: list
    tips: list
    skeleton: np.ndarray
    widths: np.ndarray

    def totalLength(self) -> float:
        return sum(s.length.smoothed for s in self.segments)

    def summary(self) -> str:
        return (f"{len(self.segments)} segments, {len(self.junctions)} junctions, "
                f"{len(self.tips)} tips, {self.totalLength():.0f} px total")


def buildGraph(mask: np.ndarray, minSegmentLength: int = 0) -> RootGraph:
    """Builds the segment graph for a binary root mask.

    minSegmentLength drops segments shorter than the given number of pixels.  It
    exists because skeleton spurs from fuzzy roots would otherwise each count as a
    segment.  Filtering here is a blunt instrument and the threshold is better
    expressed in real units once a scale is known.
    """
    skeleton = morphology.skeletonize(mask)

    #Twice the distance to the nearest background pixel is the local width.
    widths = distance_transform_edt(mask) * 2

    counts = getNeighborCounts(skeleton)
    junctionMask = (counts >= 13)
    tips = [(int(r), int(c)) for r, c in np.argwhere(counts == 11)]

    #A single branch point is usually several adjacent pixels with three or more
    #neighbours, so the pixels have to be grouped or one branch counts many times.
    junctions, pixelToJunction = clusterJunctions(junctionMask)

    #Cutting the junction pixels out leaves each unbranched run as its own component.
    segmentMask = skeleton & ~junctionMask
    components = labelComponents(segmentMask, connectivity=2)
    segments = []
    unordered = 0
    for index in range(1, components.max() + 1):
        pixels = np.argwhere(components == index)
        if len(pixels) <= minSegmentLength:
            continue

        piece = np.zeros_like(segmentMask)
        piece[pixels[:, 0], pixels[:, 1]] = True
        try:
            path = orderPath(piece)
        except ValueError:
            #A component that still branches means the junction detection missed
            #something.  Count it rather than guessing at an ordering.
            unordered += 1
            continue

        pathWidths = [widths[r, c] for r, c in path]
        segments.append(Segment(
            path=path,
            length=measurePath(path),
            meanWidth=float(np.mean(pathWidths)),
            maxWidth=float(np.max(pathWidths)),
            nodes=findAdjacentJunctions(path, pixelToJunction),
        ))

    if unordered:
        print(f"Warning: {unordered} segment(s) could not be ordered and were skipped")

    return RootGraph(segments, junctions, tips, skeleton, widths)


def clusterJunctions(junctionMask: np.ndarray):
    """Groups touching junction pixels into one node each.

    Returns the representative position of every node, and a lookup from each
    junction pixel to its node index.
    """
    components = labelComponents(junctionMask, connectivity=2)
    coordinates = np.argwhere(junctionMask)
    if len(coordinates) == 0:
        return [], {}

    grouped = {}
    for r, c in coordinates:
        grouped.setdefault(int(components[r, c]), []).append((int(r), int(c)))

    junctions = []
    pixelToJunction = {}
    for index, pixels in sorted(grouped.items()):
        centroid = np.mean(pixels, axis=0)
        #The representative has to be a real pixel, since the centroid of a bent
        #cluster can land off the skeleton.
        closest = min(pixels, key=lambda p: (p[0] - centroid[0]) ** 2 + (p[1] - centroid[1]) ** 2)

        nodeIndex = len(junctions)
        junctions.append(closest)
        for pixel in pixels:
            pixelToJunction[pixel] = nodeIndex

    return junctions, pixelToJunction


def findAdjacentJunctions(path, pixelToJunction) -> list:
    """Indices of the junction nodes touching either end of the segment."""
    found = []
    for end in (path[0], path[-1]):
        for r in range(-1, 2):
            for c in range(-1, 2):
                nodeIndex = pixelToJunction.get((end[0] + r, end[1] + c))
                if nodeIndex is not None and nodeIndex not in found:
                    found.append(nodeIndex)
    return found
