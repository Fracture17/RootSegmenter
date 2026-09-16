import os
import sys

from PIL import Image
from PIL.ImageQt import ImageQt
from PySide6 import QtWidgets


from View import View
from Model import Model
from Controller import Controller

import numpy as np


def getNextRoot(imageDirPath, labelDirPath):
    for imageName in sorted(os.listdir(imageDirPath)):
        baseImageName = os.path.splitext(imageName)[0]
        labelName = f"{baseImageName}.npz"
        labelPath = f"{labelDirPath}/{labelName}"
        if not os.path.exists(labelPath):
            return imageName, baseImageName


def compileCPP():
    pass
    os.system("c++ -shared -fPIC -Wall -Werror C++/src/GaussianThreshold.cpp -o C++/lib/GaussianThreshold.so -O3")
    os.system("c++ -shared -fPIC -Wall -Werror C++/src/EdgeFinder.cpp -o C++/lib/EdgeFinder.so -O3")
    os.system("c++ -shared -fPIC -Wall -Werror C++/src/ConnectionSearch.cpp -o C++/lib/ConnectionSearch.so -O3")
    os.system("c++ -shared -fPIC -Wall -Werror C++/src/TwoPointConnection.cpp -o C++/lib/TwoPointConnection.so -O3")
    os.system("c++ -shared -fPIC -Wall -Werror C++/src/GetClosestSkeleton.cpp -o C++/lib/GetClosestSkeleton.so -O3")
    os.system("c++ -shared -fPIC -Wall -Werror C++/src/GetClosestPointsToSegment.cpp -o C++/lib/GetClosestPointsToSegment.so -O3")


def initFiles(baseDir):
    for name in ["Labels", "Training", "TextureMatching"]:
        makeDirIfNotExists(f"{baseDir}/{name}")

    for name in ["ForegroundTextures", "BackgroundTextures"]:
        makeDirIfNotExists(f"{baseDir}/TextureMatching/{name}")


def makeDirIfNotExists(path):
    if not os.path.exists(path):
        os.mkdir(path)


if __name__ == "__main__":
    #compileCPP()

    sys.setrecursionlimit(10000)

    if len(sys.argv) != 2:
        raise SystemExit(f"Usage: python {os.path.basename(__file__)} <datasetDirectory>")

    baseDir = sys.argv[1]
    if not os.path.isdir(baseDir):
        raise SystemExit(f"Dataset directory does not exist: {baseDir}")

    initFiles(baseDir)

    app = QtWidgets.QApplication()

    imageDirPath = f"{baseDir}/Images"
    if not os.path.isdir(imageDirPath):
        raise SystemExit(f"Image directory does not exist: {imageDirPath}")

    labelDirPath = f"{baseDir}/Labels"

    nextRoot = getNextRoot(imageDirPath, labelDirPath)
    if nextRoot is None:
        raise SystemExit(f"Every image in {imageDirPath} already has a label")
    imageName, baseImageName = nextRoot

    #imagePath = "Roots/RootImages/37_3-9.png"
    #imagePath = R"RapeSeed/RootImages/C_osr_0129.jpg"

    labelSavePath = f"{labelDirPath}/{baseImageName}.npz"

    imagePath = f"{imageDirPath}/{imageName}"
    print(imagePath)
    image = Image.open(imagePath)
    if image.getbands() != ("R", "G", "B"):
        image = image.convert("RGB")

    # image = image.resize((image.width * 2, image.height * 2), Image.BICUBIC)

    #Lowercase to match the directory names on disk.  Windows matched either way,
    #but Linux is case sensitive and would silently skip the network.
    networkPath = f"{baseDir}/network"
    textureDir = f"{baseDir}/TextureMatching"
    settingsPath = f"{baseDir}/Settings.ini"

    image = np.array(image)
    view = View()
    model = Model(image)
    controller = Controller(view, model, labelSavePath, networkPath, settingsPath, textureDir)

    #m = SecondaryInfoModel(image)
    #c = SecondaryInfoController(view, m)

    # w.loadImage(imagePath)
    # v.window.loadImage(imagePath)
    # mask = np.zeros((image.size().width(), image.size().height()), dtype=np.uint8)
    # mask[100:1000, 100:1000] = 255
    # mask = ImageQt(Image.fromarray(mask))
    # v.update(image, [mask] * 1)

    app.exec()
