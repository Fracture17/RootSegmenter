import numpy as np
from PySide6.QtGui import QPixmap, QWheelEvent, QMouseEvent, QColor, QKeyEvent, QFont
from PySide6.QtWidgets import QVBoxLayout, QHBoxLayout, QWidget, QLabel, QSizePolicy, QPushButton, QCheckBox
from PySide6.QtCore import Qt, QPoint, Signal

from PhotoViewer import PhotoViewer

import screeninfo
from PIL.ImageQt import ImageQt

from MousePixelInfoBox import MousePixelInfoBox
from Model import Model


class View(QWidget):
    photoClicked = Signal(QMouseEvent, QPoint)
    keyPressed = Signal(QKeyEvent)
    mouseMoved = Signal(QPoint)

    def __init__(self):
        super(View, self).__init__()
        self.viewer = PhotoViewer(self)

        mouseInfoFont = QFont("Computer Modern", 24)
        mouseInfoFont.setBold(True)

        self.panelLayout = None

        self.infoBox = MousePixelInfoBox(self)

        self.viewer.photoClicked.connect(self._photoClicked)
        self.viewer.photoScrolled.connect(self.scrollEvent)
        self.viewer.mouseMoved.connect(self._mouseMoved)

        self.controlPanel = None

        self.invertCheckBox = QCheckBox("Invert Brightness", self)

        self.nextButton = QPushButton(self)
        self.nextButton.setText("Next")

        #The current displayed image.  Needs to exist to save reference to pixmap
        self.image = None

    def setControlPanel(self, controlPanel):
        self.controlPanel = controlPanel
        self.arrangeLayout()

    def arrangeLayout(self):
        assert self.panelLayout is None

        sizePolicy = self.controlPanel.sizePolicy()
        sizePolicy.setHorizontalPolicy(QSizePolicy.Maximum)
        sizePolicy.setVerticalPolicy(QSizePolicy.Preferred)
        self.controlPanel.setSizePolicy(sizePolicy)

        self.panelLayout = QVBoxLayout()
        self.panelLayout.addWidget(self.controlPanel)
        self.panelLayout.addWidget(self.invertCheckBox)
        self.panelLayout.addWidget(self.nextButton)
        self.panelLayout.addWidget(self.infoBox)

        mainHBLayout = QHBoxLayout(self)
        mainHBLayout.addWidget(self.viewer)
        mainHBLayout.addLayout(self.panelLayout)

    def updateControlPanel(self, newPanel):
        self.controlPanel.hide()
        self.controlPanel = newPanel
        self.controlPanel.show()
        self.panelLayout.takeAt(0)

        sizePolicy = self.controlPanel.sizePolicy()
        sizePolicy.setHorizontalPolicy(QSizePolicy.Maximum)
        sizePolicy.setVerticalPolicy(QSizePolicy.Preferred)
        self.controlPanel.setSizePolicy(sizePolicy)

        self.panelLayout.insertWidget(0, self.controlPanel)

    def showMaximized(self):
        super().showMaximized()
        m = screeninfo.get_monitors()[0]
        self.setGeometry(m.x + 0, m.y + 30, m.width, m.height - 70)
        self.setWindowFlag(Qt.WindowCloseButtonHint)

    def updateImage(self, image: ImageQt):

        self.image = image.copy()
        self.viewer.setImage(QPixmap.fromImage(self.image))

    def _photoClicked(self, event: QMouseEvent, pos: QPoint):
        self.photoClicked.emit(event, pos)

    def scrollEvent(self, event: QWheelEvent):
        self.zoom(event)

    def zoom(self, event: QWheelEvent):
        if event.angleDelta().y() > 0:
            self.zoomIn(event)
        else:
            self.zoomOut(event)

    def zoomIn(self, event: QWheelEvent):
        self.viewer.zoomIn(event.position().toPoint())

    def zoomOut(self, event: QWheelEvent):
        self.viewer.zoomOut(event.position().toPoint())

    def keyPressEvent(self, event: QKeyEvent):
        self.keyPressed.emit(event)
        super().keyPressEvent(event)

    def updateMouseInfo(self, r, c, R, G, B, intensity):
        self.infoBox.updateMouseInfo(r, c, R, G, B, intensity)

    def _mouseMoved(self, pos: QPoint):
        self.mouseMoved.emit(pos)
