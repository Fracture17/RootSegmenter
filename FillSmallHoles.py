from skimage import morphology
from skimage.measure import regionprops
import numpy as np


def fillSmallHoles(brightnesses: np.ndarray, mask: np.ndarray, maxSize: int, threshold: float):
    filledMask = morphology.remove_small_holes(mask, maxSize, connectivity=1)
    filledHoles = filledMask ^ mask
    filledHoles, numLabels = morphology.label(filledHoles, return_num=True)

    props = regionprops(filledHoles, brightnesses)
    for i in range(1, numLabels + 1):
        assert props[i - 1].label == i

        y1, x1, y2, x2 = props[i - 1].bbox
        if y1 == 0 or x1 == 0 or y2 == mask.shape[0] or x2 == mask.shape[1]:
            continue

        y1 = max(y1 - 3, 0)
        x1 = max(x1 - 3, 0)
        y2 = min(y2 + 3, mask.shape[0])
        x2 = min(x2 + 3, mask.shape[1])

        filledWindow = filledHoles[y1:y2, x1:x2]
        region = filledWindow == i

        filledPositions = np.where(region)
        filledPositions = (filledPositions[0] + y1, filledPositions[1] + x1)
        filledBrightness = np.mean(brightnesses[filledPositions])

        border = morphology.binary_dilation(region) ^ region
        borderPositions = np.where(border)
        borderPositions = (borderPositions[0] + y1, borderPositions[1] + x1)
        borderBrightness = np.mean(brightnesses[borderPositions])

        if filledBrightness / borderBrightness > threshold:
            pass
        else:
            filledMask[y1:y2, x1:x2] ^= region

    return filledMask
