import multiprocessing

from PIL import Image
from skimage.feature import local_binary_pattern
import numpy as np
import cv2
from sklearn import svm

from os import listdir
import concurrent.futures


def textureMatch(image: np.ndarray, mask: np.ndarray, foregroundTextureDir: str, backgroundTextureDir: str):
    foregroundTexturePaths = list([f"{foregroundTextureDir}/{name}" for name in listdir(foregroundTextureDir)])
    backgroundTexturePaths = list([f"{backgroundTextureDir}/{name}" for name in listdir(backgroundTextureDir)])

    if len(backgroundTexturePaths) == 0 or len(foregroundTexturePaths) == 0:
        return []

    textures = []
    for path in foregroundTexturePaths + backgroundTexturePaths:
        texture = Image.open(path)
        texture = np.array(texture)
        textures.append(texture)

    features = getFeatures(textures)
    labels = [True] * len(foregroundTexturePaths) + [False] * len(backgroundTexturePaths)
    model = svm.SVC(C=1, cache_size=5000, class_weight='balanced')
    model.fit(features, labels)

    print(model.n_support_, model.n_features_in_)
    print(model.predict(features))
    print(labels)

    TEXTURE_HEIGHT = 11
    TEXTURE_WIDTH = 11
    windows = list(getWindows(image, mask, TEXTURE_HEIGHT, TEXTURE_WIDTH))

    predictions = findParallel(windows, getFeatures, model)
    results = [x for x in predictions if x[0] == False]
    return results


def getWindows(image: np.ndarray, mask, windowHeight, windowWidth):
    assert windowHeight % 2 == 1
    assert windowWidth % 2 == 1

    windowHeight2 = windowHeight // 2
    windowWidth2 = windowWidth // 2
    positions = np.where(mask)
    positions = list(zip(*positions))
    for p in positions:
        r, c = p
        window = image[r - windowHeight2: r + windowHeight2 + 1, c - windowWidth2: c + windowWidth2 + 1]
        if window.shape[:2] != (windowHeight, windowWidth):
            continue

        yield window, p


def getFeatures(data):
    colorImages = [cv2.cvtColor(d, cv2.COLOR_RGB2Lab) for d in data]
    #brightnesses = [np.sum(d * [.299, .587, .114], axis=-1).astype(np.uint8) for d in data]

    colorHists = getColorHist(colorImages)
    #LBPHists = getLBPHist(brightnesses)

    flattenedColorHists = [x.ravel() for x in colorHists]
    #flattenedLBPHists = [x.ravel() for x in LBPHists]


    return flattenedColorHists

    mins = np.min(brightnesses, axis=(1, 2)) / 255
    #mins = np.min(brightnesses, axis=(1, 2))
    mins = mins.reshape((len(mins), 1))
    #mins = np.repeat(mins, 10, axis=-1)
    maxes = np.max(brightnesses, axis=(1, 2)) / 255
    #maxes = np.max(brightnesses, axis=(1, 2))
    maxes = maxes.reshape((len(maxes), 1))
    #maxes = np.repeat(maxes, 10, axis=-1)
    #means = np.mean(brightnesses, axis=(1, 2))
    #means = means.reshape((len(maxes), 1))

    features = np.concatenate((flattenedColorHists, flattenedLBPHists, mins, maxes), axis=-1)
    return features


def getLBPHist(data):
    R = 3
    P = R * 8

    results = []
    for d in data:
        lbp = local_binary_pattern(d, P, R, method="uniform")
        lbp_flattened = lbp.ravel()
        lbp_flattened = lbp_flattened.astype(np.uint8)

        H = cv2.calcHist([lbp_flattened], [0], None, [P + 2], [0, P + 2])
        H /= np.sum(H)
        results.append(H)

    return np.array(results)


#Assumes images are in LAB
def getColorHist(data):
    results = []
    for d in data:
        #H = cv2.calcHist([d], [1, 2], None, [8, 8], [86, 182, 87, 175])
        #H = cv2.calcHist([d], [1, 2], None, [8, 8], [72, 200, 72, 200])
        H = cv2.calcHist([d], [0, 1, 2], None, [8, 16, 16], [0, 256, 58, 203, 58, 203])
        results.append(H)

    return np.array(results)


def findParallel(windows: list, func, model):
    try:
        numCores = multiprocessing.cpu_count()
        print("CORES2", numCores)
    except:
        numCores = 1

    results = []
    with concurrent.futures.ProcessPoolExecutor() as executor:
        windowSplit = len(windows) // numCores
        windows = [windows[i * windowSplit: (i + 1) * windowSplit] for i in range(numCores)]
        futures = [executor.submit(find, x, func, model) for x in windows]

        for future in concurrent.futures.as_completed(futures):
            R = future.result()
            results.extend(R)

    return results


def find(windows, func, model):
    windowPositions = [w[1] for w in windows]
    windows = [w[0] for w in windows]

    features = func(windows)
    predictions = model.predict(features)
    results = list(zip(predictions, windowPositions))
    return results
