from PySide6.QtGui import QFont
from PySide6.QtWidgets import QVBoxLayout, QWidget, QLabel
from PySide6.QtCore import Qt, QPoint


class MousePixelInfoBox(QWidget):
    def __init__(self, parent):
        super(MousePixelInfoBox, self).__init__(parent)

        mouseInfoFont = QFont("Computer Modern", 24)
        mouseInfoFont.setBold(True)

        self.mousePositionLabel = QLabel(self)
        self.mousePositionLabel.setFont(mouseInfoFont)
        self.mouseColorLabel = QLabel(self)
        self.mouseColorLabel.setFont(mouseInfoFont)
        self.mouseIntensityLabel = QLabel(self)
        self.mouseIntensityLabel.setFont(mouseInfoFont)
        self.mouseColorProportionLabel = QLabel(self)
        self.mouseColorProportionLabel.setFont(mouseInfoFont)

        self.arrangeLayout()

    def arrangeLayout(self):
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignLeft)
        for w in [self.mousePositionLabel, self.mouseColorLabel, self.mouseIntensityLabel, self.mouseColorProportionLabel]:
            layout.addWidget(w)

    def updateMouseInfo(self, r, c, R, G, B, intensity):
        posText = f"row={r: >4}, col={c: >4}"
        self.mousePositionLabel.setText(posText)

        colorText = f"R: {R:0>3}, G: {G:0>3}, B: {B:0>3}"
        self.mouseColorLabel.setText(colorText)

        intensityText = f"intensity: {int(intensity):0>3}"
        self.mouseIntensityLabel.setText(intensityText)
        if intensity > 0:
            intensity *= 3
            proportionText = f"R: {R / intensity:0.3f}, G: {G / intensity:0.3f}, B: {B / intensity:0.3f}"
            self.mouseColorProportionLabel.setText(proportionText)
