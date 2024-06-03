import cProfile
import math

import numpy as np
from scipy.interpolate import UnivariateSpline
from skimage import morphology


import cffi
ffi_skeleton = cffi.FFI()
ffi_skeleton.cdef('''
    void getClosestSkeleton(
        unsigned char* mask,
        unsigned char* skeleton,
        int* resultsR,
        int* resultsC,
        unsigned int height, unsigned int width
    );
''')


def getClosestSkeleton(mask, skeleton):
    lib = ffi_skeleton.dlopen("C++/lib/GetClosestSkeleton.so")

    resultsR = np.full(mask.shape, -1, np.int32)
    resultsC = np.full(mask.shape, -1, np.int32)

    height, width = mask.shape

    lib.getClosestSkeleton(
        ffi_skeleton.cast('unsigned char*', mask.ctypes.data),
        ffi_skeleton.cast('unsigned char*', skeleton.ctypes.data),
        ffi_skeleton.cast('int*', resultsR.ctypes.data),
        ffi_skeleton.cast('int*', resultsC.ctypes.data),
        height, width
    )

    closestSkeletonPoints = np.empty((2,) + mask.shape, dtype=np.int32)
    closestSkeletonPoints[0] = resultsR
    closestSkeletonPoints[1] = resultsC

    return closestSkeletonPoints


def getClosestSkeletonPy(mask, skeleton):
    closestSkeletonPoints = np.full((2,) + mask.shape, -1, dtype=np.int32)
    for p in np.argwhere(mask):
        p = tuple(p)

        if skeleton[p]:
            closestSkeleton = p
        else:
            closestSkeleton = _getClosestSkeleton(mask, skeleton, p)

        closestSkeletonPoints[0, p[0], p[1]] = closestSkeleton[0]
        closestSkeletonPoints[1, p[0], p[1]] = closestSkeleton[1]

    return closestSkeletonPoints


def _getClosestSkeleton(mask, skeleton, startPos):
    frontier = [startPos]
    used = {startPos}

    minDistance = float('inf')
    limit = 1000
    bestPos = None

    i = 0
    while i < limit:
        i += 1

        newFrontier = []
        for pos in frontier:
            neighbors = getNeighbors(mask, pos, used)
            for newPos in neighbors:
                if skeleton[newPos]:
                    dY = startPos[0] - newPos[0]
                    dX = startPos[1] - newPos[1]
                    distance = math.sqrt(dY ** 2 + dX ** 2)
                    if distance < minDistance:
                        minDistance = distance
                        bestPos = newPos
                        limit = int(distance) + 1

                used.add(newPos)
                newFrontier.append(newPos)

        frontier = newFrontier

    if bestPos is not None:
        return bestPos

    raise Exception(f"No neighbors found: {startPos=}")


ffi_closest = cffi.FFI()
ffi_closest.cdef('''
    void getClosestPointsToSegment(
        unsigned char* mask,
        unsigned char* segment,
        int* closestPointsR,
        int* closestPointsC,
        unsigned char* results,
        unsigned int height, unsigned int width
    );
''')


def getClosestPointsToSegment(segment: list, mask, closestSkeletonPoints):
    lib = ffi_closest.dlopen("C++/lib/GetClosestPointsToSegment.so")

    results = np.zeros(mask.shape, np.bool_)
    segmentMask = np.zeros(mask.shape, np.bool_)
    for p in segment:
        segmentMask[p] = True

    height, width = mask.shape

    lib.getClosestPointsToSegment(
        ffi_closest.cast('unsigned char*', mask.ctypes.data),
        ffi_closest.cast('unsigned char*', segmentMask.ctypes.data),
        ffi_closest.cast('int*', closestSkeletonPoints[0].ctypes.data),
        ffi_closest.cast('int*', closestSkeletonPoints[1].ctypes.data),
        ffi_closest.cast('unsigned char*', results.ctypes.data),
        height, width,
    )

    closestPoints = [tuple(p) for p in np.argwhere(results)]
    return closestPoints


def getClosestPointsToSegmentPy(segment: list, mask, closestSkeletonPoints):
    closest = set()
    for pos in segment:
        c = floodFillClosest(pos, segment, mask, closestSkeletonPoints)
        closest |= c

    return closest


def floodFillClosest(startPos, segment: list, mask, closestSkeletonPoints):
    frontier = [startPos]
    used = {startPos}

    for _ in range(1000):
        newFrontier = []
        for pos in frontier:
            neighbors = getNeighbors(mask, pos, used)
            for newPos in neighbors:
                closest = tuple(closestSkeletonPoints[:, newPos[0], newPos[1]])
                if closest in segment:
                    used.add(newPos)
                    newFrontier.append(newPos)

        frontier = newFrontier

    return used


def getRootSegment(skeleton, startPos):
    assert skeleton[startPos], f"{startPos=}"

    neighbours = getNeighbors(skeleton, startPos)

    if len(neighbours) == 1:
        return _getRootSegment(skeleton, startPos, set())
    elif len(neighbours) == 2:
        A = _getRootSegment(skeleton, neighbours[0], {startPos})
        B = _getRootSegment(skeleton, neighbours[1], {startPos})
        return A + [startPos] + B
    else:
        candidates = []
        for p in neighbours:
            c = _getRootSegment(skeleton, p, {startPos})
            if len(c) > 1:
                candidates.append(c)
        if len(candidates) > 0:
            bestCandidate = min(candidates, key=lambda c: len(c))
            return [startPos] + bestCandidate
        else:
            return [startPos]


def _getRootSegment(skeleton, pos, used: set):
    used.add(pos)
    neighbours = getNeighbors(skeleton, pos, used)

    if len(neighbours) == 0:
        return [pos]
    elif len(neighbours) == 1:
        return [pos] + _getRootSegment(skeleton, neighbours[0], used)
    else:
        if doesNeighborBathExist(skeleton, neighbours):
            return [pos]
        else:
            return []


def getNeighbors(mask, pos, used: set = None):
    neighbours = []
    for y in range(-1, 2):
        for x in range(-1, 2):
            if y != 0 or x != 0:
                r = pos[0] + y
                c = pos[1] + x
                if 0 <= r < len(mask) and 0 <= c < len(mask[0]):
                    newPos = (r, c)
                    if used is None or newPos not in used:
                        if mask[newPos]:
                            neighbours.append(newPos)

    return neighbours


def doesNeighborBathExist(skeleton, neighbors):
    frontier = [neighbors[0]]
    used = {neighbors[0]}
    while frontier:
        p = frontier.pop()
        nextNeighbors = getNeighbors(skeleton, p, used)
        for p2 in nextNeighbors:
            if p2 in neighbors:
                used.add(p2)
                frontier.append(p2)

    return len(used) == len(neighbors)


ffi_connection = cffi.FFI()
ffi_connection.cdef('''
    void twoPointConnection(
        unsigned int startPos, unsigned int endPos,
        unsigned char* brightnesses,
        unsigned int height, unsigned int width,
        unsigned char* results,
        unsigned char* blocked
    );
''')


def twoPointConnection(startPos, endPos, brightnesses: np.ndarray):
    assert brightnesses.dtype == np.uint8

    lib = ffi_connection.dlopen("C++/lib/TwoPointConnection.so")

    results = np.zeros(brightnesses.shape, np.bool_)
    blocked = np.zeros(brightnesses.shape, np.bool_)

    height, width = brightnesses.shape
    startPosInt = startPos[0] * width + startPos[1]
    endPosInt = endPos[0] * width + endPos[1]

    lib.twoPointConnection(
        startPosInt, endPosInt,
        ffi_connection.cast('unsigned char*', brightnesses.ctypes.data),
        height, width,
        ffi_connection.cast('unsigned char*', results.ctypes.data),
        ffi_connection.cast('unsigned char*', blocked.ctypes.data),
    )

    if np.any(results):
        results = smoothConnection(startPos, endPos, results)
    return results


def smoothConnection(startPos, endPos, connection: np.ndarray):
    connection = morphology.skeletonize(connection)

    path = getConnectionPath(startPos, endPos, connection)
    if len(path) < 4:
        return connection

    T = np.arange(len(path))
    Y = [p[0] for p in path]
    X = [p[1] for p in path]
    W = [100] + [1] * (len(X) - 2) + [100]
    S = len(X) // 1.5

    splineY = UnivariateSpline(T, Y, w=W, s=S, k=3)
    splineX = UnivariateSpline(T, X, w=W, s=S, k=3)

    # t_fine = np.linspace(T.min(), T.max(), int(len(X) * 1.5))
    t_fine = np.linspace(T.min(), T.max(), int(len(X) * 2))
    Y = splineY(t_fine)
    Y = np.array([round(y) for y in Y])
    X = splineX(t_fine)
    X = np.array([round(x) for x in X])

    smoothedLabels = np.zeros(connection.shape, dtype=np.bool_)
    smoothedLabels[Y, X] = True
    smoothedLabels = morphology.skeletonize(smoothedLabels)

    return smoothedLabels


def getConnectionPath(startPos, endPos, connection: np.ndarray):
    p = startPos
    path = [p]
    while True:
        neighbors = getNeighbors(connection, p, path)
        assert len(neighbors) < 2

        p = neighbors[0]
        path.append(p)

        if p == endPos:
            return path


def getSkeletonThickness(skeleton: np.ndarray, brightnesses: np.ndarray, maxRootThickness=1):
    results = np.zeros(brightnesses.shape, dtype=np.bool_)
    mask = np.ones(brightnesses.shape, dtype=np.bool_)
    for rootPos in np.argwhere(skeleton):
        rootPos = tuple(rootPos)
        results[rootPos] = True
        startingBrightness = brightnesses[rootPos]
        brightnessThreshold = startingBrightness * .99
        frontier = [rootPos]
        used = {rootPos}
        for _ in range(maxRootThickness):
            if len(frontier) == 0:
                break

            newFrontier = []

            maxBrightness = max([int(brightnesses[p]) for p in frontier])
            brightnessThreshold = min(maxBrightness * .95, brightnessThreshold)

            for pos in frontier:
                neighbors = getNeighbors(mask, pos, used)
                for newPos in neighbors:
                    b = brightnesses[newPos]
                    if b >= brightnessThreshold:
                        used.add(newPos)
                        results[newPos] = True
                        newFrontier.append(newPos)

            frontier = newFrontier

    return results
