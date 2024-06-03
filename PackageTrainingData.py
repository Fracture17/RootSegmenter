import os

import numpy as np
from PIL import Image

#baseDir = "RapeSeed"
#baseDir = "Arabidopsis"
baseDir = R"C:\Users\johno\Documents\MainRoots"
imageDir = f"{baseDir}/Images"
labelDir = f"{baseDir}/Labels"
trainFraction = .7

images = {}
labels = {}
#for labelName in sorted(os.listdir(labelDir)):
for imageName in sorted(os.listdir(imageDir)):
    ID = imageName[:-4]
    print(ID)
    labelName = ID + ".npz"

    if not os.path.exists(f"{labelDir}/{labelName}"):
        continue

    image = Image.open(f"{imageDir}/{imageName}")
    if image.getbands() != ("R", "G", "B"):
        image = image.convert("RGB")
    image = np.array(image)
    image = image.astype(np.float16)
    image /= 255

    label = np.load(f"{labelDir}/{labelName}")
    #programLabels = label["programLabels"]
    #programLabels = programLabels.astype(np.ubyte)
    humanLabels = label["humanLabels"]
    humanLabels = humanLabels.astype(np.ubyte)

    #difference = np.zeros((*humanLabels.shape, 3), np.float16)
    #difference[:, :, 0] = humanLabels == programLabels
    #difference[:, :, 1] = (humanLabels == 1) & (programLabels == 0)
    #difference[:, :, 2] = (humanLabels == 0) & (programLabels == 1)

    #programLabels = programLabels.reshape((*programLabels.shape, 1))
    #image = np.concatenate((image, programLabels), axis=-1)
    image = image.astype(np.float16)

    images[ID] = image
    #labels[ID] = difference
    labels[ID] = humanLabels.astype(np.float16).reshape((*humanLabels.shape, 1))


#numTraining = (int(len(labels) * trainFraction) // 7) * 7
numTraining = int(len(labels) * trainFraction)

trainLabelKeys = list(labels.keys())[:numTraining]
valLabelKeys = list(labels.keys())[numTraining:]

trainLabels = {k: labels[k] for k in trainLabelKeys}
valLabels = {k: labels[k] for k in valLabelKeys}

np.savez_compressed(f"{baseDir}/Training/RootImages.npz", **images)
np.savez_compressed(f"{baseDir}/Training/TrainLabels.npz", **trainLabels)
np.savez_compressed(f"{baseDir}/Training/ValLabels.npz", **valLabels)
