"""Rasterizes an RSML file into a binary root mask.

RSML is the interchange format RootNav, SmartRoot, and the public GigaDB root
datasets use.  It stores roots as polylines rather than pixels, so comparing an
RSML label against a segmentation mask means drawing the polylines first.

The drawn width is a guess, since RSML polylines carry no thickness.  That makes
the output usable for comparing root paths, but not for measuring root diameter.

Usage: python SCRIPTS/rsml_to_mask.py <file.rsml> <width> <height> [outputName.npz]
"""

import os
import sys
import xml.etree.ElementTree as ET

import numpy as np
from PIL import Image, ImageDraw

LINE_WIDTH = 2


def getRSMLMask(path, size):
    """size is (width, height), matching PIL's convention."""
    tree = ET.parse(path)
    root = tree.getroot()

    image = Image.new('L', size, 0)
    draw = ImageDraw.Draw(image)

    polylines = root.findall('.//polyline')
    if not polylines:
        raise ValueError(f"No polylines found in {path}")

    for polyline in polylines:
        points = [(float(pt.attrib['x']), float(pt.attrib['y'])) for pt in polyline.findall('point')]
        if points:
            draw.line(points, fill=255, width=LINE_WIDTH)

    return np.array(image).astype(np.bool_)


def main():
    if len(sys.argv) not in (4, 5):
        raise SystemExit(f"Usage: python {os.path.basename(__file__)} <file.rsml> <width> <height> [outputName.npz]")

    path = sys.argv[1]
    if not os.path.isfile(path):
        raise SystemExit(f"RSML file does not exist: {path}")

    size = (int(sys.argv[2]), int(sys.argv[3]))
    mask = getRSMLMask(path, size)
    print(f"{path}: {int(mask.sum())} root pixels in {size[0]}x{size[1]}")

    if len(sys.argv) == 5:
        np.savez_compressed(sys.argv[4], mask=mask)
        print(f"Saved {sys.argv[4]}")
    else:
        Image.fromarray(mask).show()

    return 0


if __name__ == "__main__":
    sys.exit(main())
