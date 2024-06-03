from scipy.ndimage import gaussian_filter
import numpy as np

import cffi
ffi = cffi.FFI()
ffi.cdef('''
    void gaussianThreshold(
        unsigned char* smoothed,
        unsigned char* brightnesses,
        unsigned char* results,
        double threshold,
        unsigned int height, unsigned int width
    );
''')


def gaussianThreshold(brightnesses: np.ndarray, sigma: int, threshold: float):
    assert brightnesses.dtype == np.uint8

    smoothed = gaussian_filter(brightnesses, sigma=sigma)
    return brightnesses > smoothed * threshold



    results = np.zeros(brightnesses.shape, np.bool_)

    lib = ffi.dlopen('C++/lib/GaussianThreshold.so')

    lib.gaussianThreshold(
        ffi.cast('unsigned char*', smoothed.ctypes.data),
        ffi.cast('unsigned char*', brightnesses.ctypes.data),
        ffi.cast('unsigned char*', results.ctypes.data),
        threshold, brightnesses.shape[0], brightnesses.shape[1]
    )

    return results
