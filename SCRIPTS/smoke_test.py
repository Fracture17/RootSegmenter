"""Quick check that the project loads and runs on this machine.

Imports every module, calls each C++ kernel once, and loads each trained network.
This answers "is everything wired up", not "are the results good", so it uses a
small synthetic image rather than a real dataset.  Real images with untuned
thresholds make these kernels do far more work than a real session would.

Must be run from the repository root, because the kernels are opened with paths
relative to the working directory.

Usage: python SCRIPTS/smoke_test.py [--networks]
"""

import os
import sys
import time

sys.path.insert(0, os.getcwd())

import numpy as np

SIZE = 192
FAILURES = []


def check(name, func):
    start = time.time()
    try:
        detail = func()
    except Exception as e:
        FAILURES.append(name)
        print(f"  FAIL  {name}: {type(e).__name__}: {e}", flush=True)
        return
    print(f"  ok    {name} ({time.time() - start:.2f}s)  {detail}", flush=True)


def makeImage():
    """A dim background with a few bright lines standing in for roots."""
    #Very little noise on purpose.  A noisy background makes the threshold select most
    #of the image, which gives the skeleton thousands of spurious endpoints and makes
    #the connection search take minutes to check something that should take seconds.
    rng = np.random.default_rng(0)
    image = np.full((SIZE, SIZE, 3), 40, np.uint8)
    image += rng.integers(0, 2, image.shape, dtype=np.uint8)

    image[40, 20:170] = 200
    image[20:170, 96] = 210
    for i in range(60):
        image[60 + i, 40 + i] = 190

    #A deliberate gap, so the connection stage has something to join.
    image[100, 60:70] = 40
    return image


def main():
    image = makeImage()
    brightnesses = np.sum(image * [.299, .587, .114], axis=-1).astype(np.uint8)

    print(f"Imports")
    check("project modules", importModules)

    print(f"\nC++ kernels  (synthetic {SIZE}x{SIZE} image)")
    check("GaussianThreshold.so", lambda: runGauss(brightnesses))
    if hasattr(runGauss, "mask"):
        check("EdgeFinder.so", lambda: runEdges(brightnesses))
        check("ConnectionSearch.so", lambda: runConnect(brightnesses))
        check("GetClosestSkeleton.so", lambda: runSkeleton())
        check("GetClosestPointsToSegment.so", lambda: runClosestPoints())
        check("TwoPointConnection.so", lambda: runTwoPoint(brightnesses))

    if "--networks" in sys.argv:
        import glob
        print("\nTrained networks")
        for path in sorted(glob.glob("*/network*")):
            if os.path.isdir(path):
                check(path, lambda p=path: loadNetwork(p))
    else:
        print("\nTrained networks skipped, pass --networks to include them")

    print()
    if FAILURES:
        print(f"FAILED {len(FAILURES)}: {', '.join(FAILURES)}")
        return 1
    print("All checks passed.")
    return 0


def importModules():
    import Model, View, Controller, ControlPanels, PhotoViewer, MousePixelInfoBox
    import GaussianThreshold, EdgeFinder, TextureMatcher, FillSmallHoles
    import ConnectRoots, HumanCorrection
    return "12 modules"


def runGauss(brightnesses):
    from GaussianThreshold import gaussianThreshold
    runGauss.mask = gaussianThreshold(brightnesses.copy(), 3, 1.10)
    return f"{int(runGauss.mask.sum())} candidates"


def runEdges(brightnesses):
    from EdgeFinder import checkForEdges
    hit = checkForEdges(brightnesses, runGauss.mask.astype(np.uint8), 8, .9, .8, .5)
    return f"{int((hit != 0).sum())} edge pixels"


def runConnect(brightnesses):
    from ConnectRoots import connectRoots
    #connectRoots is a single pass.  connectAllRoots repeats until the mask stops
    #changing, which is the behaviour the GUI wants but far too slow for a check.
    out = connectRoots(runGauss.mask, brightnesses, 15, .8, 5)
    return f"{int(out.sum() - runGauss.mask.sum())} pixels added"


def runSkeleton():
    from HumanCorrection import getClosestSkeleton
    from skimage import morphology
    mask = runGauss.mask
    skeleton = morphology.skeletonize(mask)
    runSkeleton.skeleton = skeleton
    result = getClosestSkeleton(mask.astype(np.uint8), skeleton.astype(np.uint8))
    return f"shape {result.shape}"


def runClosestPoints():
    from HumanCorrection import getClosestSkeleton, getClosestPointsToSegment
    mask = runGauss.mask
    closest = getClosestSkeleton(mask.astype(np.uint8), runSkeleton.skeleton.astype(np.uint8))
    segment = [tuple(p) for p in np.argwhere(runSkeleton.skeleton)[:20]]
    points = getClosestPointsToSegment(segment, mask, closest)
    return f"{len(points)} points for a {len(segment)} pixel segment"


def runTwoPoint(brightnesses):
    from HumanCorrection import twoPointConnection
    result = twoPointConnection((40, 20), (40, 169), brightnesses)
    return f"{int(result.sum())} pixels along the traced root"


def loadNetwork(path):
    import tensorflow as tf
    model = tf.keras.models.load_model(path, compile=False)
    return f"input {tuple(model.input_shape)}"


if __name__ == "__main__":
    sys.exit(main())
