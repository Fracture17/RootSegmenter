import cProfile
import json
import os
from copy import deepcopy

import keras.layers
import numpy as np
import skimage
from PIL import Image
from PIL.ImageQt import ImageQt
from PySide6.QtWidgets import QMessageBox
from scipy.ndimage import gaussian_filter
from skimage import morphology
import matplotlib.path as mpltPath
import tensorflow as tf

from View import View
from Model import Model
from ControlPanels import NetworkPanel, GaussianThresholdPanel, RangeSelectionPanel, EdgeFinderPanel, TextureMatchingPanel, HoleFillPanel, MakeConnectionsPanel, RemoveSmallObjectsPanel, HumanCorrectionPanel

from PySide6.QtGui import QPixmap, QWheelEvent, QMouseEvent, QColor, QKeyEvent
from PySide6.QtCore import Signal, QPoint, QRectF, QPointF, Qt

from GaussianThreshold import gaussianThreshold
from EdgeFinder import checkForEdges
from TextureMatcher import textureMatch
from FillSmallHoles import fillSmallHoles
from ConnectRoots import connectAllRoots
from HumanCorrection import getClosestSkeleton, getRootSegment, getClosestPointsToSegment, twoPointConnection, getSkeletonThickness


class Controller:
    def __init__(self, view: View, model: Model, labelSavePath: str, networkPath: str, settingsPath: str, textureDir: str):
        self.view = view
        self.view.photoClicked.connect(self.imageClicked)
        self.view.keyPressed.connect(self.keyPressed)
        self.view.mouseMoved.connect(self.mouseMoved)
        self.view.nextButton.clicked.connect(self.nextState)

        self.model = model
        self.history = [deepcopy(self.model)]
        self.historyIndex = 0

        self.labelSavePath = labelSavePath
        self.textureDir = textureDir

        self.settingsPath = settingsPath
        if not os.path.exists(settingsPath):
            with open(settingsPath, 'w') as file:
                file.write("{}")

        if os.path.exists(networkPath):
            self.network = tf.keras.models.load_model(networkPath, compile=False)
        else:
            self.network = None

        self.shouldShowLabels = True

        self.completedProgramLabels = None

        self.controlPanels = [
            NetworkPanel(self.view),
            GaussianThresholdPanel(self.view),
            RangeSelectionPanel(self.view),
            EdgeFinderPanel(self.view),
            TextureMatchingPanel(self.view, self.textureDir),
            HoleFillPanel(self.view),
            MakeConnectionsPanel(self.view),
            RemoveSmallObjectsPanel(self.view),
            HumanCorrectionPanel(self.view),
        ]

        for panel in self.controlPanels:
            panel.hide()

            panel.loadSettings(settingsPath)

        if self.network is None:
            self.model.state = 1
            self.history = []

        with open(settingsPath, 'r') as file:
            settings = json.load(file)
        if "Invert Brightness" in settings:
            self.shouldInvertBrightness = settings["Invert Brightness"]
        else:
            self.shouldInvertBrightness = False

        if self.shouldInvertBrightness:
            self.view.invertCheckBox.click()
            self.model.brightnesses = 255 - self.model.brightnesses
        self.view.invertCheckBox.stateChanged.connect(self.invertBrightness)

        self.view.controlPanel = self.controlPanels[self.model.state]
        self.view.controlPanel.show()
        self.view.arrangeLayout()
        self.updateView()
        self.view.showMaximized()

        self.runFunction()

    def updateView(self):
        composite = self.createViewImage()
        self.view.updateImage(ImageQt(composite))

        for node in self.model.selectionNodes:
            self.view.viewer.addOverlayEllipse(node[1] - 2, node[0] - 2, 5, 5, "Red")

        if len(self.model.selectionNodes) > 1:
            B = self.model.selectionNodes[1:] + [self.model.selectionNodes[0]]
            for nodeA, nodeB in zip(self.model.selectionNodes, B):
                self.view.viewer.addOverlayLine(nodeA[1], nodeA[0], nodeB[1], nodeB[0], "Red")

        if self.model.addSegmentStartPos is not None:
            pos = self.model.addSegmentStartPos
            self.view.viewer.addOverlayEllipse(pos[1] - 2, pos[0] - 2, 5, 5, "Red")

        self.view.updateControlPanel(self.controlPanels[self.model.state])

    def createViewImage(self):
        composite = Image.fromarray(self.model.image.copy())
        if self.shouldShowLabels:
            for label in self.model.labels:
                layer = Image.fromarray(label.mask).convert("L")
                composite.paste(Image.new("RGB", layer.size, label.color), (0, 0), layer)

        return composite

    def imageClicked(self, event: QMouseEvent, pos: QPoint):
        if self.model.state == 2:
            pos = (pos.y(), pos.x())
            self.model.selectionNodes.append(pos)

            self.shouldShowLabels = True
            self.updateView()
            self.updateHistory()
        elif self.model.state == 4:
            print(event.buttons())
            #Left click shows up as NoButton because of how dragging is implemented
            #NoButton doesn't appear to be triggered in other ways, so seems to work fine
            if event.buttons() == Qt.NoButton or event.buttons() == Qt.RightButton:
                if event.buttons() == Qt.NoButton:
                    directory = f"{self.textureDir}/BackgroundTextures"
                else:
                    directory = f"{self.textureDir}/ForegroundTextures"

                self.savePatch(pos.y(), pos.x(), directory)

            self.view.controlPanel.reloadImages()
        elif self.model.state == 8:
            pos = (pos.y(), pos.x())

            if event.buttons() == Qt.RightButton:
                if not self.removeSegment(pos):
                    return
            elif event.buttons() in [Qt.NoButton, Qt.LeftButton]:
                if self.model.addSegmentStartPos is None:
                    self.model.addSegmentStartPos = pos
                else:
                    startPos = self.model.addSegmentStartPos
                    self.model.addSegmentStartPos = None
                    if event.modifiers() == Qt.ShiftModifier:
                        self.addLine(startPos, pos)
                    else:
                        self.addSegment(startPos, pos)
            else:
                if event.modifiers() == Qt.ControlModifier:
                    radius = 100
                elif event.modifiers() == Qt.ShiftModifier:
                    radius = 20
                #elif event.modifiers() & Qt.ShiftModifier and event.modifiers() & Qt.ControlModifier:
                elif event.modifiers() == Qt.AltModifier:
                    radius = 1.1
                else:
                    radius = 5

                self.removeSegmentsInRadius(pos, radius)

            self.shouldShowLabels = True
            self.updateView()
            self.updateHistory()

    def savePatch(self, r, c, saveDirectory):
        image = Image.fromarray(self.model.image)
        HEIGHT = 11
        WIDTH = 11
        assert HEIGHT % 2 == 1
        assert WIDTH % 2 == 1

        patch = image.crop((c - WIDTH // 2, r - HEIGHT // 2, c + WIDTH // 2 + 1, r + HEIGHT // 2 + 1))

        i = 0
        while True:
            path = f"{saveDirectory}/Texture_{i}.png"
            if not os.path.exists(path):
                patch.save(path)
                break
            i += 1

    def removeSegmentsInRadius(self, clickPos, radius):
        self.model.clearLabel(7)
        self.model.clearLabel(8)

        radiusInt = int(radius)
        for y in range(-radiusInt, radiusInt + 1):
            for x in range(-radiusInt, radiusInt + 1):
                if (y ** 2 + x ** 2) ** .5 < radius:
                    r = clickPos[0] + y
                    c = clickPos[1] + x
                    if 0 <= r < len(self.model.image) and 0 <= c < len(self.model.image[0]):
                        self.model.labels[5].mask[r, c] = False
                        self.model.labels[7].mask[r, c] = False

    def removeSegment(self, clickPos, shouldClearRemoved: bool = True):
        mask = self.model.labels[5].mask
        if not mask[clickPos]:
            return False

        closestSkeletonPos = self.model.closestSkeletonFromMask[:, clickPos[0], clickPos[1]]
        closestSkeletonPos = tuple(closestSkeletonPos)
        closestSegment = getRootSegment(self.model.skeleton, closestSkeletonPos)

        if shouldClearRemoved:
            self.model.clearLabel(7)
            self.model.clearLabel(8)

        closestPoints = getClosestPointsToSegment(closestSegment, mask, self.model.closestSkeletonFromMask)

        for p in closestPoints:
            self.model.labels[7].mask[p] = True
            self.model.labels[5].mask[p] = False

        return True

    def addLine(self, startPos, endPos):
        self.model.clearLabel(7)
        self.model.clearLabel(8)

        line = np.linspace(startPos, endPos, num=1000, dtype=np.int32)
        Y = line[:, 0]
        X = line[:, 1]

        lineMask = np.zeros(self.model.brightnesses.shape, dtype=np.bool_)
        lineMask[Y, X] = True

        maxRootThickness = int(self.view.controlPanel.getValues()[0])
        root = getSkeletonThickness(lineMask, self.model.brightnesses, maxRootThickness)
        self.model.labels[5].mask |= root
        if not self.model.usingNeuralNet:
            self.model.labels[5].mask = fillSmallHoles(self.model.brightnesses, self.model.labels[5].mask,
                                                       *self.controlPanels[5].getValues())

        self.model.skeleton = morphology.skeletonize(self.model.labels[5].mask)
        self.model.closestSkeletonFromMask = getClosestSkeleton(self.model.labels[5].mask, self.model.skeleton)

    def addSegment(self, startPos, endPos):
        self.model.clearLabel(7)
        self.model.clearLabel(8)

        connection = twoPointConnection(startPos, endPos, self.model.brightnesses)

        if np.all(connection == False):
            self.addLine(startPos, endPos)
            return

        maxRootThickness = int(self.view.controlPanel.getValues()[0])
        root = getSkeletonThickness(connection, self.model.brightnesses, maxRootThickness)
        self.model.labels[5].mask |= root
        #if not self.model.usingNeuralNet:
        #self.model.labels[5].mask = fillSmallHoles(self.model.brightnesses, self.model.labels[5].mask, *self.controlPanels[5].getValues())

        self.model.skeleton = morphology.skeletonize(self.model.labels[5].mask)
        self.model.closestSkeletonFromMask = getClosestSkeleton(self.model.labels[5].mask, self.model.skeleton)

    def keyPressed(self, event: QKeyEvent):
        if event.key() == Qt.Key_Z:
            if event.modifiers() & Qt.ShiftModifier:
                self.redo()
            else:
                self.undo()
        elif event.key() == Qt.Key_X:
            self.shouldShowLabels ^= True
            self.updateView()
        elif event.key() == Qt.Key_Return or event.key() == Qt.Key_Enter:
            if self.model.state == 0:
                self.model.state = len(self.controlPanels) - 1
                self.model.usingNeuralNet = True

                self.shouldShowLabels = True
                self.updateView()
                self.updateHistory()
            if self.model.state == 2:
                if event.modifiers() == Qt.ShiftModifier:
                    self.runRootSelection(True)
                else:
                    self.runRootSelection(False)
            else:
                self.runFunction()
        elif event.key() == Qt.Key_N:
            self.nextState()


        elif event.key() == Qt.Key_S:
            skeleton = morphology.skeletonize(self.model.labels[5].mask)
            self.model.labels[7].mask = skeleton
            self.updateView()
            self.updateHistory()

    def runFunction(self):
        state = self.model.state

        if state == 0:
            self.runInitial()
        elif state == 1:
            self.runGauss()
        elif state == 2:
            pass
        elif state == 3:
            self.runEdgeChecker()
        elif state == 4:
            self.runTextureMatcher()
        elif state == 5:
            self.runFillSMallHoles()
        elif state == 6:
            self.runMakeConnections()
        elif state == 7:
            self.runRemoveSmallObjects()
        elif state == 8:
            self.runHumanCorrection()

        self.view.controlPanel.saveSettings(self.settingsPath)

        self.shouldShowLabels = True
        self.updateView()
        self.updateHistory()

    def runInitial(self):
        if self.network is None:
            return

        image = self.model.image.copy()
        image = image.astype(np.float32)
        image /= 255
        image.resize((1, *image.shape))

        result = self.network(image)

        result = np.array(result)
        result = result.reshape(*result.shape[1:-1])
        result = result > .5

        prunedMask = morphology.remove_small_objects(result, min_size=4, connectivity=2)
        newMask = connectAllRoots(prunedMask, self.model.brightnesses, *self.controlPanels[6].getValues())
        newMask |= result

        results = morphology.remove_small_objects(newMask, min_size=10, connectivity=2)

        self.model.labels[5].mask = results

    def runGauss(self):
        self.model.clearLabel(5)

        print("Gauss")
        brightnesses = self.model.brightnesses.copy()
        results = gaussianThreshold(brightnesses, *self.view.controlPanel.getValues())
        self.model.labels[1].mask = results

    def runRootSelection(self, invert: bool = False):
        if len(self.model.selectionNodes) >= 3:
            polygon = np.array(self.model.selectionNodes)
            mask = self.getPointsInPolygon(polygon)

            if invert:
                mask = ~mask

            self.model.labels[1].mask = np.where(mask, self.model.labels[1].mask, False)

            self.model.selectionNodes = []

            self.shouldShowLabels = True
            self.updateView()
            self.updateHistory()

    def getPointsInPolygon(self, polygon):
        path = mpltPath.Path(polygon)

        x, y = np.meshgrid(np.arange(self.model.brightnesses.shape[1]),
                           np.arange(self.model.brightnesses.shape[0]))  # Adjust size as needed
        points = np.vstack((y.flatten(), x.flatten())).T

        inside = path.contains_points(points)

        mask = inside.reshape(self.model.brightnesses.shape)

        return mask

    def runEdgeChecker(self):
        print("Edge")

        self.model.selectionNodes = []

        brightnesses = self.model.brightnesses
        targets = self.model.labels[1].mask.astype(np.uint8)
        edgeHit = checkForEdges(brightnesses, targets, *self.view.controlPanel.getValues())

        positions = np.where(self.model.labels[1].mask)
        self.model.clearLabel(2)
        self.model.labels[2].mask[positions] = True

        edgePositions = np.where((edgeHit != 0) & self.model.labels[1].mask)
        self.model.clearLabel(3)
        self.model.labels[3].mask[edgePositions] = True
        self.model.labels[2].mask[edgePositions] = False

    def runTextureMatcher(self):
        self.model.clearLabel(1)
        self.model.clearLabel(3)

        results = textureMatch(self.model.image, self.model.labels[2].mask, f"{self.textureDir}/ForegroundTextures",
                               f"{self.textureDir}/BackgroundTextures")

        mask = np.zeros(self.model.labels[0].mask.shape, dtype=np.bool_)
        for _, p in results:
            mask[p] = True
        print(self.model.labels[3].mask.shape)
        print(mask.shape)
        self.model.labels[3].mask = mask

    def runFillSMallHoles(self):
        self.model.labels[2].mask ^= self.model.labels[3].mask
        self.model.clearLabel(4)
        self.model.clearLabel(3)

        self.model.labels[5].mask = self.model.labels[2].mask

        #mask = (self.model.labels[2].mask ^ self.model.labels[4].mask) & self.model.labels[2].mask
        mask = fillSmallHoles(self.model.brightnesses, self.model.labels[5].mask, *self.view.controlPanel.getValues())
        self.model.labels[6].mask = mask ^ self.model.labels[5].mask

    def runMakeConnections(self):
        self.model.labels[5].mask |= self.model.labels[6].mask
        self.model.clearLabel(6)

        prunedMask = morphology.remove_small_objects(self.model.labels[5].mask, min_size=4, connectivity=2)
        newMask = connectAllRoots(prunedMask, self.model.brightnesses, *self.view.controlPanel.getValues())
        newMask |= self.model.labels[5].mask
        connected = self.model.labels[5].mask ^ newMask
        self.model.labels[7].mask = connected

    def runRemoveSmallObjects(self):
        self.model.labels[5].mask |= self.model.labels[7].mask
        self.model.clearLabel(7)

        self.model.labels[5].mask = fillSmallHoles(self.model.brightnesses, self.model.labels[5].mask,
                                                   *self.controlPanels[5].getValues())

        prunedMask = morphology.remove_small_objects(self.model.labels[5].mask, *self.view.controlPanel.getValues(),
                                                     connectivity=2)

        removedObjects = self.model.labels[5].mask ^ prunedMask
        self.model.labels[8].mask = removedObjects

        self.completedProgramLabels = self.model.labels[5].mask ^ self.model.labels[8].mask

    def runHumanCorrection(self):
        self.model.clearLabel(1)
        self.model.clearLabel(2)

        self.model.labels[5].mask ^= self.model.labels[8].mask
        self.model.clearLabel(8)

        mask = self.model.labels[5].mask
        self.model.skeleton = morphology.skeletonize(mask)

        self.model.closestSkeletonFromMask = getClosestSkeleton(mask, self.model.skeleton)

    def nextState(self):
        print("Next", self.model.state)
        if self.model.state == len(self.controlPanels) - 1:
            print("Next End")
            np.savez(self.labelSavePath, humanLabels=self.model.labels[5].mask)

            x = QMessageBox(text="Label Saved!")
            x.exec()
        else:
            self.model.state += 1

            self.updateView()
            self.runFunction()
        print("Next", self.model.state)

    def mouseMoved(self, pos: QPoint):
        r, c = pos.y(), pos.x()

        if r < 0 or r >= self.model.image.shape[0] or c < 0 or c >= self.model.image.shape[1]:
            return

        R, G, B = self.model.image[r, c]
        intensity = self.model.brightnesses[r, c]

        self.view.updateMouseInfo(r, c, R, G, B, intensity)

    def updateHistory(self):
        self.historyIndex += 1
        if self.historyIndex > 100:
            self.historyIndex = 100
            self.history.pop(0)

        #Remove future history
        self.history = self.history[:self.historyIndex]

        self.history.append(deepcopy(self.model))

    def undo(self):
        if self.historyIndex > 0:
            self.historyIndex -= 1
            self.model = deepcopy(self.history[self.historyIndex])

            self.shouldShowLabels = True
            self.updateView()

    def redo(self):
        if self.historyIndex < (len(self.history) - 1):
            self.historyIndex += 1
            self.model = deepcopy(self.history[self.historyIndex])

            self.shouldShowLabels = True
            self.updateView()

    def invertBrightness(self):
        print("Invert")
        print(self.shouldInvertBrightness)
        self.shouldInvertBrightness = not self.shouldInvertBrightness
        print(self.shouldInvertBrightness)

        with open(self.settingsPath, 'r') as file:
            settings = json.load(file)

        settings["Invert Brightness"] = self.shouldInvertBrightness

        with open(self.settingsPath, 'w') as file:
            json.dump(settings, file, indent=4)

        self.model.brightnesses = 255 - self.model.brightnesses
