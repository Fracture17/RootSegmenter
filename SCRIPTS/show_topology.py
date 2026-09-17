"""Draws the segment graph over a root image so it can be checked by eye.

Every segment gets its own colour, junctions are marked in red, and tips in
cyan.  The point is to make the topology visible before any heuristic decides
which segments belong to the same root, because the mistakes are visual and will
not show up in summary numbers.

Writes a full view and a zoomed crop, since junctions are a few pixels wide and
invisible at full image scale.

Usage: python SCRIPTS/show_topology.py <image> <label.npz> [outputPrefix]
"""

import os
import sys

sys.path.insert(0, os.getcwd())

import numpy as np
from PIL import Image

from RootTopology import buildGraph

#Distinguishable in sequence, and none of them are the red or cyan used for nodes.
PALETTE = [
    (255, 196, 0), (0, 200, 120), (150, 130, 255), (255, 120, 190),
    (120, 220, 255), (200, 230, 60), (255, 150, 60), (140, 200, 160),
    (220, 160, 255), (180, 220, 120),
]
JUNCTION_COLOR = (255, 40, 40)
TIP_COLOR = (0, 255, 255)
MIN_SEGMENT_LENGTH = 3


def drawMarker(canvas, positions, color, radius=3):
    height, width = canvas.shape[:2]
    for r, c in positions:
        rows = slice(max(r - radius, 0), min(r + radius + 1, height))
        cols = slice(max(c - radius, 0), min(c + radius + 1, width))
        canvas[rows, cols] = color


def render(image, graph):
    canvas = (image * .35).astype(np.uint8)

    for i, segment in enumerate(graph.segments):
        color = PALETTE[i % len(PALETTE)]
        for r, c in segment.path:
            canvas[r, c] = color

    drawMarker(canvas, graph.tips, TIP_COLOR, radius=2)
    drawMarker(canvas, graph.junctions, JUNCTION_COLOR, radius=2)
    return canvas


def densestCrop(mask, size=520):
    """Finds the most root dense window, which is where the topology is hardest."""
    height, width = mask.shape
    size = min(size, height, width)
    step = max(size // 4, 1)

    best, bestCount = (0, 0), -1
    for r in range(0, height - size + 1, step):
        for c in range(0, width - size + 1, step):
            count = int(mask[r:r + size, c:c + size].sum())
            if count > bestCount:
                best, bestCount = (r, c), count
    return best[0], best[1], size


def main():
    if len(sys.argv) not in (3, 4):
        raise SystemExit(f"Usage: python {os.path.basename(__file__)} <image> <label.npz> [outputPrefix]")

    imagePath, labelPath = sys.argv[1], sys.argv[2]
    prefix = sys.argv[3] if len(sys.argv) > 3 else "topology"

    image = Image.open(imagePath)
    if image.getbands() != ("R", "G", "B"):
        image = image.convert("RGB")
    image = np.array(image)

    mask = np.load(labelPath)["humanLabels"]
    if mask.shape != image.shape[:2]:
        raise SystemExit(f"Label shape {mask.shape} does not match image {image.shape[:2]}")

    graph = buildGraph(mask, minSegmentLength=MIN_SEGMENT_LENGTH)
    print(graph.summary())

    lengths = sorted((s.length.smoothed for s in graph.segments), reverse=True)
    widths = [s.meanWidth for s in graph.segments]
    print(f"longest segments (px): {', '.join(f'{v:.0f}' for v in lengths[:8])}")
    print(f"segment length median {np.median(lengths):.1f}, mean width {np.mean(widths):.2f} px")

    shortCount = sum(1 for v in lengths if v < 20)
    print(f"{shortCount} of {len(lengths)} segments are under 20 px, "
          f"which is where fuzz and real laterals are hard to tell apart")

    canvas = render(image, graph)
    Image.fromarray(canvas).save(f"{prefix}-full.png")
    print(f"Wrote {prefix}-full.png")

    r, c, size = densestCrop(mask)
    crop = canvas[r:r + size, c:c + size]
    crop = np.array(Image.fromarray(crop).resize((size * 2, size * 2), Image.NEAREST))
    Image.fromarray(crop).save(f"{prefix}-crop.png")
    print(f"Wrote {prefix}-crop.png  (2x view of the densest {size}x{size} region at row {r}, col {c})")

    return 0


if __name__ == "__main__":
    sys.exit(main())
