"""Checks the length estimators against shapes whose lengths are known exactly.

Each shape is rasterized the way a skeleton would be, measured, and compared to
its analytic length.  This is the only part of the measurement pipeline that can
be checked without a human deciding what counts as a root, so it is worth
pinning down before anything harder is built on it.

Writes a figure showing every shape with its true and measured lengths, so the
numbers can be spot checked against what the curve actually looks like.

Usage: python SCRIPTS/validate_length.py [outputImage.png]
"""

import os
import sys

sys.path.insert(0, os.getcwd())

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from skimage import morphology

from RootMeasurement import measurePath, orderPath

SIZE = 260
#63 pixels per inch on the main dataset, which is 24.803 per cm.
PIXELS_PER_CM = 63 / 2.54
#A tolerance the estimator should comfortably meet on clean synthetic curves.
TOLERANCE = .02


def rasterize(points):
    """Marks the nearest pixel for each sampled point, then thins the result.

    Dense sampling sets redundant pixels, so the raw mask is not a clean one pixel
    curve.  Skeletonizing is also what the real pipeline does to a root mask, so
    the estimator sees the same kind of input either way.
    """
    mask = np.zeros((SIZE, SIZE), np.bool_)
    for y, x in points:
        r, c = int(round(y)), int(round(x))
        if 0 <= r < SIZE and 0 <= c < SIZE:
            mask[r, c] = True
    return morphology.skeletonize(mask)


def sampleLine(y0, x0, y1, x1):
    n = int(max(abs(y1 - y0), abs(x1 - x0)) * 4) + 2
    t = np.linspace(0, 1, n)
    return list(zip(y0 + t * (y1 - y0), x0 + t * (x1 - x0))), float(np.hypot(y1 - y0, x1 - x0))


def sampleArc(centerY, centerX, radius, startAngle, endAngle):
    n = int(abs(endAngle - startAngle) * radius * 4) + 2
    a = np.linspace(startAngle, endAngle, n)
    points = list(zip(centerY + radius * np.sin(a), centerX + radius * np.cos(a)))
    return points, float(abs(endAngle - startAngle) * radius)


def sampleSine(x0, x1, amplitude, wavelength, baseline):
    n = int((x1 - x0) * 8) + 2
    x = np.linspace(x0, x1, n)
    k = 2 * np.pi / wavelength
    y = baseline + amplitude * np.sin(k * x)
    #Arc length of the analytic curve, integrated finely.
    dense = np.linspace(x0, x1, 200000)
    derivative = amplitude * k * np.cos(k * dense)
    trueLength = float(np.trapz(np.sqrt(1 + derivative ** 2), dense))
    return list(zip(y, x)), trueLength


def buildShapes():
    shapes = []

    points, trueLength = sampleLine(30, 20, 30, 220)
    shapes.append(("horizontal", points, trueLength))

    points, trueLength = sampleLine(20, 20, 220, 220)
    shapes.append(("45 degree diagonal", points, trueLength))

    #The worst case for counting steps.  A shallow angle becomes a staircase.
    points, trueLength = sampleLine(40, 20, 100, 230)
    shapes.append(("16 degree shallow", points, trueLength))

    points, trueLength = sampleArc(130, 130, 100, np.pi * .75, np.pi * 2.25)
    shapes.append(("arc, radius 100", points, trueLength))

    points, trueLength = sampleSine(20, 240, 30, 110, 130)
    shapes.append(("sine wave", points, trueLength))

    return shapes


def main():
    outputPath = sys.argv[1] if len(sys.argv) > 1 else "length-validation.png"

    shapes = buildShapes()
    figure, axes = plt.subplots(1, len(shapes), figsize=(4 * len(shapes), 4.8))

    failures = []
    print(f"{'shape':<20}{'true':>9}{'stepped':>10}{'err':>8}{'smoothed':>11}{'err':>8}{'cm':>8}")
    for ax, (name, points, trueLength) in zip(axes, shapes):
        mask = rasterize(points)
        path = orderPath(mask)
        length = measurePath(path)

        steppedError = (length.stepped - trueLength) / trueLength
        smoothedError = (length.smoothed - trueLength) / trueLength
        centimetres = length.inUnits(PIXELS_PER_CM)

        print(f"{name:<20}{trueLength:>9.2f}{length.stepped:>10.2f}{steppedError:>+7.1%}"
              f"{length.smoothed:>11.2f}{smoothedError:>+7.1%}{centimetres:>8.2f}")

        if abs(smoothedError) > TOLERANCE:
            failures.append(f"{name} smoothed error {smoothedError:+.1%}")

        ax.imshow(mask, cmap="gray_r", interpolation="nearest")
        ax.set_title(
            f"{name}\ntrue {trueLength:.1f} px\n"
            f"stepped {length.stepped:.1f} ({steppedError:+.1%})\n"
            f"smoothed {length.smoothed:.1f} ({smoothedError:+.1%})",
            fontsize=10)
        ax.axis("off")

    figure.suptitle(
        f"Length estimator against known shapes.  Smoothed is the one used.  "
        f"Scale {PIXELS_PER_CM:.2f} px/cm.", fontsize=12)
    figure.tight_layout()
    os.makedirs(os.path.dirname(outputPath) or ".", exist_ok=True)
    figure.savefig(outputPath, dpi=110)
    print(f"\nWrote {outputPath}")

    if failures:
        print(f"\nFAILED: {'; '.join(failures)}")
        return 1
    print(f"\nAll shapes within {TOLERANCE:.0%}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
