from collections import defaultdict
from math import atan2
from statistics import median

import numpy as np
from scipy.ndimage import convolve
from skimage import morphology
from skimage.measure import label

import cffi
ffi = cffi.FFI()
ffi.cdef('''
    void connectionSearch(
        unsigned char* brightnesses,
        unsigned char* mask,
        unsigned int height, unsigned int width,
        unsigned int searchLimit,
        unsigned int* endpoints,
        double* targetAngles,
        unsigned char* brightnessThresholds,
        unsigned int numEndpoints
    );
''')


def connectAllRoots(mask: np.ndarray, brightnesses: np.ndarray, searchDistance, threshold: float, minSegmentLength):
    searchDistance = int(searchDistance)
    minSegmentLength = int(minSegmentLength)

    mask = mask.copy()
    currentMask = mask.copy()
    i = 0
    while True:
        mask = connectRoots(mask, brightnesses, searchDistance, threshold, minSegmentLength)
        if np.all(mask == currentMask):
            break
        currentMask = mask.copy()
        print(i)
        i += 1
    print("total", i + 1)

    return mask


def connectRoots(mask: np.ndarray, brightnesses: np.ndarray, searchDistance, threshold: float, minSegmentLength):
    candidates = getExtendCandidates(mask, minSegmentLength)
    endpoints = []
    targetAngles = []
    averageBrightnesses = []
    used = set()
    for c in candidates:
        startPos = c[0]
        directionEndPos = c[minSegmentLength - 1]

        dy = directionEndPos[0] - startPos[0]
        dx = startPos[1] - directionEndPos[1]
        angle = atan2(dy, dx)

        if (startPos, angle) not in used:
            used.add((startPos, angle))

            endpoints.append(startPos)
            targetAngles.append(angle)
            averageBrightnesses.append(int(median(float(brightnesses[p]) for p in c[:minSegmentLength])))

    return connectionSearch(brightnesses, mask, endpoints, targetAngles, averageBrightnesses, searchDistance, threshold)


def getExtendCandidates(region: np.ndarray, minSegmentLength):
    skeleton = morphology.skeletonize(region)

    kernel = np.array([
        [1, 1, 1],
        [1, 10, 1],
        [1, 1, 1],
    ])
    numNeighbors = convolve(skeleton.astype(np.uint8), kernel, mode='constant', cval=0)

    endPoints = np.where(numNeighbors == 11)
    endPoints = list(zip(*endPoints))
    endPoints = [(y.item(), x.item()) for y, x in endPoints]

    points = np.where(numNeighbors >= 11)
    points = list(zip(*points))
    points = {(y.item(), x.item()) for y, x in points}

    adjacent = defaultdict(list)
    for pos in points:
        for y in range(-1, 2):
            for x in range(-1, 2):
                if y != 0 or x != 0:
                    newPos = (pos[0] + y, pos[1] + x)
                    if newPos in points:
                        adjacent[pos].append(newPos)

    candidates = []
    for p in endPoints:
        segments = getEndSegments(p, adjacent, 15, [])
        if len(segments) > 0:
            for segment in segments:
                for i in range(len(segment) - minSegmentLength - 1):
                    straight = getStraightSegment(segment[i:])
                    if len(straight) >= minSegmentLength:
                        direction = (straight[0][0] - straight[1][0], straight[0][1] - straight[1][1])
                        oppositePos = (straight[0][0] + direction[0], straight[0][1] + direction[1])
                        if isInBounds(oppositePos, skeleton) and not skeleton[oppositePos]:
                            candidates.append(straight)

                        break

    return candidates


def isInBounds(pos, matrix):
    return 0 <= pos[0] < len(matrix) and 0 <= pos[1] < len(matrix[1])


def getEndSegments(pos, adjacent, length: int, invalidOptions: list, previous: list = None):
    if previous is None:
        previous = []
    else:
        previous = previous.copy()

    invalidOptions = invalidOptions.copy()

    for i in range(1, length + 1):
        previous.append(pos)

        neighbors = [p for p in adjacent[pos] if p not in previous and p not in invalidOptions]

        if len(neighbors) > 1:
            invalidOptions.extend(neighbors)
            segments = []
            for n in neighbors:
                branchSegments = getEndSegments(n, adjacent, length - i, invalidOptions, previous)
                branchSegments = [s for s in branchSegments if len(s) > 0]
                #segments.extend(previous + x for x in branchSegments)
                segments.extend(branchSegments)
            return segments
        elif len(neighbors) == 1:
            newPos = neighbors[0]
            pos = newPos
        else:
            return [previous]

    return [previous]


class CrawlerDirections:
    FORWARD = 0
    RIGHT = 1
    LEFT = 2
    DIRECTIONS = [FORWARD, RIGHT, LEFT]
    MAPPING = {
        (1, 0): ((1, -1), (1, 1)),
        (1, -1): ((0, -1), (1, 0)),
        (0, -1): ((-1, -1), (1, -1)),
        (-1, -1): ((-1, 0), (0, -1)),
        (-1, 0): ((-1, 1), (-1, -1)),
        (-1, 1): ((0, 1), (-1, 0)),
        (0, 1): ((1, 1), (-1, 1)),
        (1, 1): ((1, 0), (0, 1)),
    }


def getStraightSegment(segment):
    directions = []
    for a, b in zip(segment, segment[1:]):
        d = (a[0] - b[0], a[1] - b[1])
        directions.append(d)

    firstDirection = directions[0]
    allowedDirections = [*CrawlerDirections.MAPPING[firstDirection]]
    canDeviate = True
    numDeviations = 0
    for i, d in enumerate(directions, start=1):
        if d != firstDirection:
            if d in allowedDirections and canDeviate:
                allowedDirections = [d]
                #canDeviate = False
                numDeviations += 1
                if numDeviations > len(segment) // 2:
                    return segment[:i]
            else:
                return segment[:i]
        else:
            canDeviate = True
    return segment


def connectionSearch(brightnesses: np.ndarray, mask: np.ndarray, endpoints, targetAngles, targetBrightnesses, searchDistance, threshold: float):
    lib = ffi.dlopen('C++/lib/ConnectionSearch.so')

    brightnesses = brightnesses.astype(np.uint8)
    height, width = brightnesses.shape[0], brightnesses.shape[1]
    targetAngles = np.array(targetAngles, dtype=np.float64)
    #Maybe convert this to using median?
    brightnessThresholds = [int(b * threshold) for b in targetBrightnesses]
    brightnessThresholds = np.array(brightnessThresholds, dtype=np.uint8)
    endpoints = [r * width + c for r, c in endpoints]
    endpoints = np.array(endpoints, dtype=np.uint32)
    numEndpoints = len(endpoints)
    print(numEndpoints)
    mask = mask.copy()

    lib.connectionSearch(
        ffi.cast('unsigned char*', brightnesses.ctypes.data),
        ffi.cast('unsigned char*', mask.ctypes.data),
        height, width, searchDistance,
        ffi.cast('unsigned int*', endpoints.ctypes.data),
        ffi.cast('double*', targetAngles.ctypes.data),
        ffi.cast('unsigned char*', brightnessThresholds.ctypes.data),
        numEndpoints
    )

    return mask
