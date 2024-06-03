import numpy as np
from skimage import morphology
from scipy.interpolate import CubicSpline, UnivariateSpline

from dataclasses import dataclass
from typing import NamedTuple


import cffi
ffi = cffi.FFI()
ffi.cdef('''
    void trace(
        unsigned short* brightnesses, unsigned char* labels,
        unsigned char* allowed,
        unsigned char* used, unsigned int* usedOrder,
        unsigned int height, unsigned int width,
        unsigned int startR, unsigned int startC,
        unsigned int endR, unsigned int endC,
        unsigned int limit
    );
''')


import os


#TODO: Move these somewhere better
class Color(NamedTuple):
    R: int
    G: int
    B: int


@dataclass
class Label:
    name: str
    mask: np.ndarray
    color: Color


class Model:
    def __init__(self, image: np.ndarray):
        self.labels = [
            Label("Background", np.zeros(image.shape[:-1], np.bool_), Color(0, 0, 0)),
            Label("", np.zeros(image.shape[:-1], np.bool_), Color(0, 255, 0)),
            Label("", np.zeros(image.shape[:-1], np.bool_), Color(255, 0, 0)),
            Label("", np.zeros(image.shape[:-1], np.bool_), Color(0, 0, 0)),
            Label("", np.zeros(image.shape[:-1], np.bool_), Color(100, 100, 100)),
            Label("", np.zeros(image.shape[:-1], np.bool_), Color(0, 0, 255)),
            Label("", np.zeros(image.shape[:-1], np.bool_), Color(14, 174, 238)),
            Label("", np.zeros(image.shape[:-1], np.bool_), Color(255, 105, 0)),
            Label("", np.zeros(image.shape[:-1], np.bool_), Color(0, 0, 0)),
            Label("", np.zeros(image.shape[:-1], np.bool_), Color(255, 192, 203)),
            Label("", np.zeros(image.shape[:-1], np.bool_), Color(255, 255, 0)),
            Label("", np.zeros(image.shape[:-1], np.bool_), Color(100, 255, 0)),
        ]

        self.bfsStartPosition = None
        self.progressiveSearchLimit = 0

        self.state = 0

        self.closestSkeletonFromMask = None
        self.skeleton = None

        self.selectionNodes = []

        self.addSegmentStartPos = None

        self.usingNeuralNet = False

        self.image = image
        weighted = self.image * [.299, .587, .114]
        self.brightnesses = np.sum(weighted, axis=-1).astype(np.uint8)

    def setBFSStartPosition(self, r, c):
        assert self.bfsStartPosition is None
        self.bfsStartPosition = (r, c)

    def BFS(self, endR, endC):
        assert self.bfsStartPosition is not None

        brightnesses = np.sum(self.image, axis=-1)

        r, c = self.bfsStartPosition
        self.bfsStartPosition = None
        frontier = {(brightnesses[r, c], r, c)}
        used = {r, c}

        while frontier:
            b, r, c = max(frontier)
            frontier.remove((b, r, c))

            # SECONDARY_ROOT_UNATTACHED
            self.labels[2].mask[r, c] = True

            # SECONDARY_ROOT_UNATTACHED_ENDPOINT
            if r == endR and c == endC:
                # if self.labels[1].mask[r, c]:
                break

            for y in range(r - 1, r + 2):
                if 0 <= y < len(self.image):
                    for x in range(c - 1, c + 2):
                        if 0 <= x < len(self.image[0]):
                            p = (y, x)
                            p2 = (brightnesses[p], y, x)
                            if p2 not in used:
                                frontier.add(p2)
                                used.add(p2)

    def findShortestLine(self, r, c, endR, endC):
        self.labels[2].mask = np.zeros(self.labels[2].mask.shape, np.bool_)
        self.trace(r, c, endR, endC)

        #self.labels[1].mask = self.labels[2].mask.copy()
        self.labels[2].mask = morphology.skeletonize(self.labels[2].mask)

        r, c = self.getClosest(r, c)
        endR, endC = self.getClosest(endR, endC)

        self.labels[2].mask[r, c] = True
        self.labels[2].mask[endR, endC] = True
        #kernel = np.ones((3, 3), np.uint8)
        #x = self.labels[2].mask.astype(np.uint8)
        #self.labels[2].mask = cv2.dilate(x, kernel, iterations=1).astype(np.bool_)
        shortestPath = self.breadthFirstSearch(r, c, endR, endC)
        #self.labels[2].mask = np.zeros(self.labels[2].mask.shape, np.bool_)

        T = np.arange(len(shortestPath))
        Y = [p[0] for p in shortestPath]
        X = [p[1] for p in shortestPath]
        W = [100] + [1] * (len(X) - 2) + [100]
        #S = len(X) // ((len(X) / 2000) ** 2)
        S = len(X) // 1.5
        #S = 10000
        print(len(X), S)

        splineY = UnivariateSpline(T, Y, w=W, s=S)
        splineX = UnivariateSpline(T, X, w=W, s=S)

        t_fine = np.linspace(T.min(), T.max(), int(len(X) * 1.5))
        Y = splineY(t_fine)
        Y = [round(y) for y in Y]
        X = splineX(t_fine)
        X = [round(x) for x in X]

        shortestPath2 = list(zip(Y, X))

        self.labels[2].mask = np.zeros(self.labels[2].mask.shape, np.bool_)
        #threshold = None
        """thresholds = []
        for p in shortestPath2:
            #threshold = self.thresholdRadius(p[0], p[1], threshold)
            if thresholds:
                t = mean(thresholds)
            else:
                t = None
            x = self.thresholdRadius(p[0], p[1], t)
            thresholds.append(x)"""

        for p in shortestPath:
            self.labels[1].mask[p] = True
            self.labels[2].mask[p] = False

        for p in shortestPath2:
            self.labels[6].mask[p] = True
            self.labels[2].mask[p] = False

    def findMiddleLine(self, r, c, endR, endC):
        self.labels[2].mask = np.zeros(self.labels[2].mask.shape, np.bool_)
        self.trace(r, c, endR, endC)

        #self.labels[1].mask = self.labels[2].mask.copy()
        self.labels[2].mask = morphology.skeletonize(self.labels[2].mask)

        r, c = self.getClosest(r, c)
        endR, endC = self.getClosest(endR, endC)

        self.labels[2].mask[r, c] = True
        self.labels[2].mask[endR, endC] = True
        #kernel = np.ones((3, 3), np.uint8)
        #x = self.labels[2].mask.astype(np.uint8)
        #self.labels[2].mask = cv2.dilate(x, kernel, iterations=1).astype(np.bool_)
        shortestPath = self.breadthFirstSearch(r, c, endR, endC)
        #self.labels[2].mask = np.zeros(self.labels[2].mask.shape, np.bool_)

        self.labels[1].mask = np.zeros(self.labels[1].mask.shape, np.bool_)
        self.labels[2].mask = np.zeros(self.labels[2].mask.shape, np.bool_)
        for p in shortestPath:
            self.thresholdRadius(p[0], p[1])

        self.labels[1].mask = np.zeros(self.labels[1].mask.shape, np.bool_)
        brightnesses = np.sum(self.image, axis=-1)
        root = np.where(self.labels[2].mask)
        root = list(zip(root[0], root[1]))
        root = sorted(root, key=lambda p: brightnesses[p])
        print("ROOT", len(root))
        a = 0
        b = 128
        a2 = a
        while True:
            while a < b:
                self.labels[2].mask[root[a]] = False
                a += 1

            path = self.breadthFirstSearch(r, c, endR, endC)
            if path is not None:
                if b == len(root):
                    break

                print(a, b - a2)
                a = b
                #b += 100
                if b - a2 == 128:
                    b += 128
                else:
                    b += max((b - a2) // 2, 1)
                a2 = a
                if b > len(root):
                    b = len(root)
            else:
                while a > a2:
                    a -= 1
                    self.labels[2].mask[root[a]] = True
                b = (b + a) // 2
                if a == b:
                    a += 1
                    b += 128 + 1
                    if b > len(root):
                        b = len(root)
                    a2 += 1

        for p in shortestPath:
            if self.labels[2].mask[p]:
                self.labels[3].mask[p] = True
            else:
                self.labels[1].mask[p] = True
            #self.labels[2].mask[p] = False

    def trace(self, r, c, endR, endC, *, allowed: np.array = None, limit: int = None):
        brightnesses = np.sum(self.image, axis=-1, dtype=np.uint16)
        labels = self.labels[4].mask.copy()
        usedOrder = np.zeros(self.image.shape[:-1], dtype=np.uint32)
        used = np.zeros(self.image.shape[:-1], dtype=np.uint8)
        height = self.image.shape[0]
        width = self.image.shape[1]

        if allowed is None:
            allowed = np.ones(self.image.shape[:-1], dtype=np.uint8)

        if limit is None:
            limit = 10 ** 6

        lib = ffi.dlopen('C++/out/libtrace.so')
        lib.trace(
            ffi.cast('unsigned short*', brightnesses.ctypes.data),
            ffi.cast('unsigned char*', labels.ctypes.data),
            ffi.cast('unsigned char*', allowed.ctypes.data),
            ffi.cast('unsigned char*', used.ctypes.data),
            ffi.cast('unsigned int*', usedOrder.ctypes.data),
            height, width, r, c, endR, endC, limit
        )
        #lib.trace(brightnesses, labels, used, usedOrder, height, width, r, c, endR, endC, 10 ** 5)

        self.labels[4].mask = labels

    def tracePython(self, r, c, endR, endC):
        brightnesses = np.sum(self.image, axis=-1)

        frontier = {(brightnesses[r, c], r, c)}
        used = {r, c}

        while frontier:
            b, r, c = max(frontier)
            frontier.remove((b, r, c))

            # SECONDARY_ROOT_UNATTACHED
            self.labels[2].mask[r, c] = True

            #SECONDARY_ROOT_UNATTACHED_ENDPOINT
            if r == endR and c == endC:
            #if self.labels[1].mask[r, c]:
                break

            for y in range(r - 1, r + 2):
                if 0 <= y < len(self.image):
                    for x in range(c - 1, c + 2):
                        if 0 <= x < len(self.image[0]):
                            p = (y, x)
                            p2 = (brightnesses[p], y, x)
                            if p2 not in used:
                                frontier.add(p2)
                                used.add(p2)

    def trace2(self, r, c, endR, endC):
        brightnesses = np.sum(self.image, axis=-1)

        frontier = {(brightnesses[r, c], r, c)}
        used = {r, c}

        while frontier:
            b, r, c = max(frontier)
            frontier.remove((b, r, c))

            numNeighbors = 0
            for y in range(r - 1, r + 2):
                if 0 <= y < len(self.image):
                    for x in range(c - 1, c + 2):
                        if 0 <= x < len(self.image[0]):
                            p = (y, x)
                            if self.labels[2].mask[p]:
                                numNeighbors += 1
            if numNeighbors >= 2:
                continue

            # SECONDARY_ROOT_UNATTACHED
            self.labels[2].mask[r, c] = True

            #SECONDARY_ROOT_UNATTACHED_ENDPOINT
            if r == endR and c == endC:
            #if self.labels[1].mask[r, c]:
                break

            for y in range(r - 1, r + 2):
                if 0 <= y < len(self.image):
                    for x in range(c - 1, c + 2):
                        if 0 <= x < len(self.image[0]):
                            p = (y, x)
                            p2 = (brightnesses[p], y, x)
                            if p2 not in used:
                                frontier.add(p2)
                                used.add(p2)

    def breadthFirstSearch(self, r, c, endR, endC):
        frontier = {(r, c, ((r, c),))}
        used = {(r, c)}

        while frontier:
            newFrontier = set()
            for (r, c, path) in frontier:
                #print(r, c)

                # SECONDARY_ROOT_UNATTACHED_ENDPOINT
                if r == endR and c == endC:
                    return path

                for y in range(r - 1, r + 2):
                    if 0 <= y < len(self.image):
                        for x in range(c - 1, c + 2):
                            if 0 <= x < len(self.image[0]):
                                if self.labels[2].mask[y, x]:
                                    p = (y, x)
                                    if p not in used:
                                        used.add(p)
                                        newPath = path + (p,)
                                        newFrontier.add((y, x, newPath))

            frontier = newFrontier

        return None

    def deleteRadius(self, r, c, radius):
        for y in range(r - radius, r + radius):
            if 0 <= y <= self.image.shape[0]:
                for x in range(c - radius, c + radius):
                    if 0 <= x <= self.image.shape[1]:
                        for L in self.labels:
                            L.mask[y, x] = False

    def startProgressiveSearch(self, r, c):
        self.setBFSStartPosition(r, c)
        self.progressiveSearchLimit = 0

    def clearLabel(self, labelNum):
        self.labels[labelNum].mask = np.zeros(self.labels[labelNum].mask.shape, np.bool_)

    def progressiveSearch(self, limit):
        self.progressiveSearchLimit += limit

        allowed = self.labels[3].mask.astype(np.uint8)
        if np.all(allowed == False):
            allowed = np.ones(allowed.shape, dtype=np.uint8)
        self.trace(self.bfsStartPosition[0], self.bfsStartPosition[1], 10000, 10000, allowed=allowed, limit=self.progressiveSearchLimit)
