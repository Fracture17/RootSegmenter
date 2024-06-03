import json

from PySide6.QtGui import QPixmap, QWheelEvent, QMouseEvent, QColor, QKeyEvent, QDoubleValidator, QIntValidator, QFont
from PySide6.QtWidgets import QVBoxLayout, QHBoxLayout, QWidget, QLabel, QLineEdit, QSizePolicy, QGridLayout, \
    QScrollArea, QMessageBox
from PySide6.QtCore import Signal, Qt, QTimer, QSize

import os
from functools import partial


class CustomLineEdit(QLineEdit):
    def keyPressEvent(self, event):
        super().keyPressEvent(event)
        if event.key() == Qt.Key_Return or event.key() == Qt.Key_Enter:
            QTimer.singleShot(0, self.setFocus)


class ControlPanel(QWidget):
    def __init__(self, mainTitleText: str, subTitleTexts: list[str], parent: QWidget):
        super().__init__(parent)

        self.layout = QVBoxLayout(self)

        mainTitleLabel = QLabel(self)
        mainTitleLabel.setText(mainTitleText)
        mainTitleFont = QFont("Arial", 24)
        mainTitleFont.setBold(True)
        mainTitleLabel.setFont(mainTitleFont)
        self.layout.addWidget(mainTitleLabel)

        subTitleFont = QFont("Arial", 12)
        subTitleFont.setBold(True)
        for text in subTitleTexts:
            subTitleLabel = QLabel(self)
            subTitleLabel.setText(text)
            subTitleLabel.setFont(subTitleFont)
            self.layout.addWidget(subTitleLabel)

        self.labels = []
        self.entries = []

    def addEntry(self, labelText: str, defaultValue: str, validator=None):
        label = QLabel(self)
        label.setText(labelText)
        entry = CustomLineEdit(self)
        entry.setText(defaultValue)

        if validator is not None:
            entry.setValidator(validator)

        self.layout.addWidget(label)
        self.layout.addWidget(entry)

        self.labels.append(label)
        self.entries.append(entry)

    def addDummyEntry(self):
        dummy = QLabel()
        policy = dummy.sizePolicy()
        policy.setVerticalPolicy(QSizePolicy.Expanding)
        policy.setHorizontalPolicy(QSizePolicy.Expanding)
        dummy.setSizePolicy(policy)
        self.layout.addWidget(dummy)

    def getValues(self):
        return [float(entry.text()) for entry in self.entries]

    def loadSettings(self, settingsPath: str):
        with open(settingsPath, 'r') as file:
            settings = json.load(file)

        name = str(self.__class__)
        if name in settings:
            for label, entry in zip(self.labels, self.entries):
                if label.text() in settings[name]:
                    newText = str(settings[name][label.text()])
                    entry.setText(newText)

    def saveSettings(self, settingsPath: str):
        with open(settingsPath, 'r') as file:
            settings = json.load(file)

        entries = {label.text(): entry.text() for label, entry in zip(self.labels, self.entries)}
        settings[str(self.__class__)] = entries

        with open(settingsPath, 'w') as file:
            json.dump(settings, file, indent=4)


class NetworkPanel(ControlPanel):
    def __init__(self, parent):
        mainTitleText = "Neural Network"
        subTitleTexts = [
            "Press enter to use neural network predictions",
            "Press next to use normal program"
        ]

        super().__init__(mainTitleText, subTitleTexts, parent)

        self.addDummyEntry()


class GaussianThresholdPanel(ControlPanel):
    def __init__(self, parent):
        mainTitleText = "Gaussian Threshold"
        subTitleTexts = [
            "Blurs the image and selects pixels that are darker after being smoothed",
            "Identifies pixels that are brighter than their neighbors"
        ]

        super().__init__(mainTitleText, subTitleTexts, parent)

        self.addEntry("Standard Deviation of the Gaussian.  A higher value means a larger blur area", "5", QIntValidator())
        self.addEntry("Brightness Threshold.  Multiple of the smoothed brightness.  Higher values are more restrictive", "1.04", QDoubleValidator())

        self.addDummyEntry()


class RangeSelectionPanel(ControlPanel):
    def __init__(self, parent):
        mainTitleText = "Crop"
        subTitleTexts = [
            "Selects the root area",
        ]

        super().__init__(mainTitleText, subTitleTexts, parent)

        self.addDummyEntry()


class EdgeFinderPanel(ControlPanel):
    def __init__(self, parent):
        mainTitleText = "Edge Finder"
        subTitleTexts = [
            "Removes fuzzy edges from roots"
        ]

        super().__init__(mainTitleText, subTitleTexts, parent)

        self.addEntry("Search Distance", "2", QIntValidator())
        self.addEntry("Soft Edge Upper Threshold", ".92", QDoubleValidator())
        self.addEntry("Soft Edge Lower Threshold", "1.05", QDoubleValidator())
        self.addEntry("Hard Edge Threshold", ".7", QDoubleValidator())

        self.addDummyEntry()


class TextureMatchingPanel(ControlPanel):
    def __init__(self, parent, textureDir: str):
        mainTitleText = "Texture Matching"
        subTitleTexts = [
            "Uses color information to remove background labels",
            "Left click the image to select an example of the background",
            "Right click to select an example of the foreground",
            "Double click the saved images to delete them"
        ]

        super().__init__(mainTitleText, subTitleTexts, parent)

        self.imageListsLayout = QHBoxLayout()

        self.textureDir = textureDir
        self.backgroundImageDisplay = ImageListWidget(f"{self.textureDir}/BackgroundTextures", "Background")
        self.imageListsLayout.addWidget(self.backgroundImageDisplay)
        self.foregroundImageDisplay = ImageListWidget(f"{self.textureDir}/ForegroundTextures", "Foreground")
        self.imageListsLayout.addWidget(self.foregroundImageDisplay)

        self.layout.addLayout(self.imageListsLayout)

    def reloadImages(self):
        self.backgroundImageDisplay.reloadImages()
        self.foregroundImageDisplay.reloadImages()


class ImageListWidget(QWidget):
    def __init__(self, imageDir: str, title: str):
        super().__init__()

        self.images = []

        self.scrollArea = QScrollArea(self)
        self.scrollArea.setWidgetResizable(True)

        self.container = QWidget()
        self.containerLayout = QVBoxLayout()
        self.container.setLayout(self.containerLayout)
        self.scrollArea.setWidget(self.container)

        self.mainLayout = QVBoxLayout()
        self.titleLabel = QLabel(title)
        self.mainLayout.addWidget(self.titleLabel)
        self.mainLayout.addWidget(self.scrollArea)
        self.setLayout(self.mainLayout)

        self.imageDir = imageDir
        self.reloadImages()

    def addImage(self, imagePath):
        label = ClickableImageLabel(imagePath)
        self.containerLayout.addWidget(label)

        imageIndex = len(self.images)
        label.doubleClicked.connect(partial(self.imageClicked, imageIndex))
        self.images.append((label, imagePath))

    def imageClicked(self, imageIndex):
        reply = QMessageBox.question(self, 'Confirm Delete',
                                     "Do you want to delete this image?",
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.removeImage(imageIndex)

    def removeImage(self, imageIndex):
        print(imageIndex)
        label, imagePath = self.images.pop(imageIndex)
        os.remove(imagePath)
        self.containerLayout.removeWidget(label)
        label.deleteLater()

        self.reloadImages()

    def reloadImages(self):
        for x, y in self.images:
            self.containerLayout.removeWidget(x)
            x.deleteLater()

        self.images = []
        files = os.listdir(self.imageDir)
        paths = [f"{self.imageDir}/{name}" for name in files]
        paths = sorted(paths, key=lambda p: os.path.getmtime(p), reverse=True)
        for p in paths:
            self.addImage(p)


class ClickableImageLabel(QLabel):
    doubleClicked = Signal()

    def __init__(self, imagePath, parent=None):
        super().__init__(parent)

        self.imagePath = imagePath
        pixmap = QPixmap(imagePath)
        scaledPixmap = pixmap.scaled(QSize(165, 165), Qt.KeepAspectRatio)
        self.setPixmap(scaledPixmap)

    def mouseDoubleClickEvent(self, event):
        self.doubleClicked.emit()


class HoleFillPanel(ControlPanel):
    def __init__(self, parent):
        mainTitleText = "Fill Small Holes"
        subTitleTexts = [
            "Fills small holes in labels",
            "Uses relative brightness to avoid filling legitimate holes"
        ]

        super().__init__(mainTitleText, subTitleTexts, parent)

        self.addEntry("Max Hole Size", "10", QIntValidator())
        self.addEntry("Brightness Threshold.  Higher values are more restrictive", ".99", QDoubleValidator())

        self.addDummyEntry()


class MakeConnectionsPanel(ControlPanel):
    def __init__(self, parent):
        mainTitleText = "Connect Seperated Roots"
        subTitleTexts = [
            "Connects parts of roots that are disconnected"
        ]

        super().__init__(mainTitleText, subTitleTexts, parent)

        self.addEntry("Search Distance", "13", QIntValidator())
        self.addEntry("Brightness Threshold.  Higher values are more restrictive", ".95", QDoubleValidator())
        self.addEntry("Min Segment Length", "6", QIntValidator())

        self.addDummyEntry()


class RemoveSmallObjectsPanel(ControlPanel):
    def __init__(self, parent):
        mainTitleText = "Remove Small Objects"
        subTitleTexts = [
            "Removes small objects that are unlikely to be roots"
        ]

        super().__init__(mainTitleText, subTitleTexts, parent)

        self.addEntry("Max Object Size", "200", QIntValidator())

        self.addDummyEntry()


class HumanCorrectionPanel(ControlPanel):
    def __init__(self, parent):
        mainTitleText = "Manual Correction"
        subTitleTexts = [
            "Manually fix any errors left by the previous stages",
            "Middle click mouse to remove all labels in a radius",
            "Make the radius bigger by holding Shift or Control",
            "Right click to remove a label segment",
            "Left click to trace a root",
            "First click sets the start position, and the second sets the end position",
            "Hold Shift on the second click to draw a straight line",
            "Press next when finished to save results"
        ]

        super().__init__(mainTitleText, subTitleTexts, parent)

        self.addEntry("Max Root Width", "1", QIntValidator())

        self.addDummyEntry()
