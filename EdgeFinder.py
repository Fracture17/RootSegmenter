import numpy as np


import cffi
ffi = cffi.FFI()
ffi.cdef('''
    void checkForEdges(
        unsigned char* brightnesses,
        unsigned char* edgeHit,
        unsigned int* targets,
        unsigned int numTargets,
        unsigned int maxDistance,
        double upperThreshold, double lowerThreshold,
        double hardEdgeThreshold,
        unsigned int height, unsigned int width
    );
''')


def checkForEdges(brightnesses: np.ndarray, targets: np.ndarray, maxDistance, upperThreshold, lowerThreshold, hardEdgeThreshold):
    assert brightnesses.dtype == np.uint8
    assert targets.dtype == np.uint8

    height, width = brightnesses.shape

    targetPositions = np.where(targets)
    targetPositions = list(zip(*targetPositions))
    targetPositions = [r * width + c for r, c in targetPositions if r > 20 and r < height - 20 and c > 20 and c < width - 20]
    #targetPositions = [r * width + c for r, c in targetPositions]

    return _checkForEdges(brightnesses, targetPositions, maxDistance, upperThreshold, lowerThreshold, hardEdgeThreshold)


def _checkForEdges(brightnesses: np.ndarray, targets: list, maxDistance, upperThreshold, lowerThreshold, hardEdgeThreshold):
    edgeHit = np.zeros(brightnesses.shape, dtype=np.uint8)
    targets = np.array(targets).astype(np.uint32)
    print(targets.shape)

    lib = ffi.dlopen('C++/lib/EdgeFinder.so')

    lib.checkForEdges(
        ffi.cast('unsigned char*', brightnesses.ctypes.data),
        ffi.cast('unsigned char*', edgeHit.ctypes.data),
        ffi.cast('unsigned int*', targets.ctypes.data),
        len(targets),
        int(maxDistance),
        upperThreshold, lowerThreshold,
        hardEdgeThreshold,
        brightnesses.shape[0], brightnesses.shape[1]
    )

    return edgeHit
